"""
Gemini Intelligence Service.

Extracts structured resume intelligence using Google Gemini API:
- Candidate profile summary
- Categorized technical & professional skills
- Grounded strengths with concrete textual evidence
- Actionable, constructive improvement recommendations with examples
- Targeted matching job roles

Safety & Hallucination Guardrails:
- Strictly instructs Gemini to only extract evidence grounded in the resume text.
- Formatted output validated via Pydantic schemas.
- Handles rate limits, missing keys, and transient network errors cleanly.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ValidationError

from app.core.config import GEMINI_API_KEY
from app.models.candidate import CandidateType

logger = logging.getLogger(__name__)

CURRENT_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
CURRENT_PROMPT_VERSION = "v1.1"

API_KEY_REGEX = re.compile(r"AIza[0-9A-Za-z-_]{20,50}")
QUERY_KEY_REGEX = re.compile(r"(key=)[^&\s]+", re.IGNORECASE)


def mask_sensitive_data(text: str) -> str:
    """Masks Google API keys and sensitive tokens in error messages and logs."""
    if not text:
        return ""
    masked = API_KEY_REGEX.sub("[REDACTED_API_KEY]", str(text))
    masked = QUERY_KEY_REGEX.sub(r"\1[REDACTED_API_KEY]", masked)
    return masked


def is_transient_error(exc: Exception) -> bool:
    """
    Determines whether an exception is transient (503, 429, timeout, network reset).
    Authentication, invalid argument, bad request, and schema validation errors are never retried.
    """
    exc_str = str(exc).lower()

    # Never retry authentication, invalid request, or schema validation
    non_transient = [
        "api_key_invalid", "permission_denied", "unauthenticated",
        "invalid_argument", "401", "403", "400", "bad request",
        "validationerror", "jsondecodeerror"
    ]
    if any(marker in exc_str for marker in non_transient):
        return False

    transient = [
        "503", "unavailable", "overloaded", "resource_exhausted", "429",
        "rate limit", "quota", "timeout", "timed out", "connection",
        "remote disconnected", "reset by peer", "service unavailable"
    ]
    return any(marker in exc_str for marker in transient)


class StrengthItem(BaseModel):
    anchor: str = Field(..., min_length=2, max_length=120, description="Project, role, or resume section providing supporting evidence")
    statement: str = Field(..., min_length=3, max_length=500, description="Proven candidate capability or quantified outcome")

    def to_display_string(self) -> str:
        clean_anchor = self.anchor.strip("[]: ")
        return f"[{clean_anchor}]: {self.statement.strip()}"


class ContextualSkillItem(BaseModel):
    skill: str = Field(..., min_length=2, max_length=100, description="Demonstrated skill name")
    evidence: str = Field(..., min_length=5, max_length=500, description="Verbatim resume excerpt demonstrating this skill")


class SkillCategorizationSchema(BaseModel):
    explicit: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Skills directly named by candidate in skills, coursework, or experience sections",
    )
    contextual: Dict[str, List[Union[ContextualSkillItem, str]]] = Field(
        default_factory=dict,
        description="Skills clearly demonstrated through projects or accomplishments with verbatim evidence excerpts",
    )


class GeminiImprovementSchema(BaseModel):
    category: str = Field(..., min_length=2, max_length=50, description="Area of improvement, e.g. Impact, Sections, Formatting, Skills")
    issue: str = Field(..., min_length=3, max_length=500, description="Specific weakness or gap observed in the resume text")
    recommendation: str = Field(..., min_length=3, max_length=500, description="Concrete recommendation explaining how to address the issue")
    example: Optional[str] = Field(default=None, max_length=500, description="Before-and-after example illustrating the improvement")


class GeminiAnalysisOutput(BaseModel):
    summary: str = Field(default="", min_length=5, max_length=2000, description="Executive professional summary")
    skills_categorized: Union[SkillCategorizationSchema, Dict[str, List[str]]] = Field(
        default_factory=dict,
        description="Categorized dictionary of technical and functional skills present in the resume",
    )
    strengths: List[Union[StrengthItem, str]] = Field(
        default_factory=list,
        max_length=10,
        description="Candidate strengths grounded in specific project/role evidence (may be empty if evidence is insufficient)",
    )
    improvements: List[GeminiImprovementSchema] = Field(
        default_factory=list,
        max_length=10,
        description="Actionable improvement recommendations with concrete examples (may be empty if resume has no major issues)",
    )
    suggested_roles: List[str] = Field(
        default_factory=list,
        max_length=8,
        description="Industry job roles matching the candidate's verified background and seniority",
    )
    missing_or_uncertain_elements: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="Candidate-appropriate absent or ambiguous resume elements observed without guessing",
    )



GEMINI_SYSTEM_INSTRUCTION = """
You are ResumeIQ Intelligence Engine, an expert technical career auditor and talent intelligence advisor.
Your mission is to perform an objective, strictly grounded, and evidence-based analysis of the provided resume text.

CORE PRINCIPLES & ANTI-HALLUCINATION RULES:
1. FACTUAL GROUNDING: Every skill, strength, and achievement you report must be explicitly supported by textual evidence in the resume.
2. ZERO HALLUCINATION: NEVER invent, fabricate, assume, or extrapolate qualifications, employers, degrees, tools, technologies, or metrics that are not in the text.
3. EXPLICIT VS CONTEXTUAL TOOLS: Explicit skills are tools/languages directly named in the resume text. Contextual skills are capabilities clearly demonstrated through projects or accomplishments without a standalone bullet, and MUST include an exact verbatim evidence excerpt copied directly from the resume text demonstrating the skill. Do not infer unmentioned tools.
4. DYNAMIC SKILL BUCKETS: Only include skill categories that contain at least one verified skill from the resume. Do NOT output empty categories.
5. GROUNDED STRENGTHS: Every strength must explicitly reference the specific project, role, or quantified achievement where it was demonstrated (format: "[Project or Role Name]: <Specific proven competency and outcome>").
6. SPECIFIC IMPROVEMENTS: Never output generic advice (e.g., "add certifications", "use action verbs"). Tie each recommendation to an identifiable bullet point, project, or section in the resume text, explaining exactly what is missing and providing a concrete before-and-after example.
7. CALIBRATED SENIORITY: Suggested roles must strictly match the candidate's verified experience level and seniority.
"""


def build_analysis_prompt(resume_text: str, candidate_type: CandidateType) -> str:
    # Seniority & evaluation guidance based on candidate type
    if candidate_type == CandidateType.student:
        guidance = (
            "CANDIDATE TYPE: STUDENT (University / College)\n"
            "- EVALUATION FOCUS: Prioritize academic coursework, technical projects, open-source contributions, hackathons, and foundational computer science / domain skills.\n"
            "- FAIRNESS: Do NOT penalize the student for lacking commercial work experience or multi-million dollar business metrics.\n"
            "- SENIORITY CALIBRATION FOR SUGGESTED ROLES: Suggest strictly student-level opportunities such as Software Engineering Intern, Research Assistant, Co-op Developer, or Junior Trainee. Never suggest senior or mid-level titles.\n"
            "- IMPROVEMENTS FOCUS: Advise on project documentation, GitHub repositories, testing, and quantifying project scale (e.g. users, test coverage, benchmark speedups)."
        )
    elif candidate_type == CandidateType.fresher:
        guidance = (
            "CANDIDATE TYPE: FRESHER (Recent Graduate / Entry-Level)\n"
            "- EVALUATION FOCUS: Evaluate practical project depth, internships, capstone projects, core technical stack, and software engineering foundations.\n"
            "- SENIORITY CALIBRATION FOR SUGGESTED ROLES: Suggest graduate and entry-level positions such as Associate Software Engineer, Junior Backend Developer, Graduate Trainee, or Entry-Level QA Engineer.\n"
            "- IMPROVEMENTS FOCUS: Advise on transitioning academic projects to production-grade engineering standards (CI/CD, code review, automated testing, containerization)."
        )
    else:  # Experienced
        guidance = (
            "CANDIDATE TYPE: EXPERIENCED PROFESSIONAL\n"
            "- EVALUATION FOCUS: Scrutinize professional work history, architectural scope, quantifiable business and technical metrics, leadership, system scale, and operational reliability.\n"
            "- SENIORITY CALIBRATION FOR SUGGESTED ROLES: Suggest mid-level, senior, or lead roles accurately calibrated to their demonstrated years of experience and technical breadth.\n"
            "- IMPROVEMENTS FOCUS: Identify bullet points lacking business impact, scale, or metrics ($ revenue/costs, % latency reduction, QPS, uptime) and advise on executive clarity."
        )

    return f"""
{guidance}

Please analyze the following extracted resume text according to your system instructions:

--- RESUME TEXT START ---
{resume_text}
--- RESUME TEXT END ---

Return valid JSON conforming to this schema:
{{
  "summary": "2-3 sentence executive professional summary grounded in verified experience.",
  "skills_categorized": {{
    "explicit": {{
      "Languages": ["verified language 1", "verified language 2"],
      "Frameworks & Libraries": ["verified framework 1"]
    }},
    "contextual": {{
      "Tools & Platforms": [
        {{
          "skill": "verified contextual skill 1",
          "evidence": "Exact verbatim sentence or bullet from resume text demonstrating this skill"
        }}
      ]
    }}
  }},
  "strengths": [
    {{
      "anchor": "Project or Role Anchor",
      "statement": "Evidence-grounded candidate strength with outcome or metric"
    }}
  ],
  "improvements": [
    {{
      "category": "Impact",
      "issue": "Identifiable issue grounded in a specific project or section (e.g. 'Project Alpha lacks performance metrics')",
      "recommendation": "Actionable, candidate-level recommendation on how to resolve it",
      "example": "Before: '...' -> After: '...'"
    }}
  ],
  "suggested_roles": [
    "Role 1 (Strictly matching {candidate_type.value} seniority)",
    "Role 2 (Strictly matching {candidate_type.value} seniority)",
    "Role 3 (Strictly matching {candidate_type.value} seniority)"
  ],
  "missing_or_uncertain_elements": [
    "Specific missing or ambiguous element appropriate to candidate level, if any"
  ]
}}

"""



class GeminiServiceError(Exception):
    """Exception raised when Gemini API call fails."""
    pass


def run_gemini_analysis(
    resume_text: str,
    candidate_type: CandidateType,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> GeminiAnalysisOutput:
    """
    Calls Google Gemini API using the official google-genai SDK.
    Parses and validates the structured output.
    """
    effective_api_key = api_key or GEMINI_API_KEY
    if not effective_api_key:
        raise GeminiServiceError("Gemini API key is not configured. Please set GEMINI_API_KEY in the backend .env file.")

    effective_model = model_name or os.getenv("GEMINI_MODEL", CURRENT_MODEL_NAME)


    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=effective_api_key,
            http_options=types.HttpOptions(timeout=60.0),
        )
        prompt = build_analysis_prompt(resume_text, candidate_type)

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=effective_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=GEMINI_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        temperature=0.2,  # Low temperature for deterministic, fact-grounded extraction
                    ),
                )

                raw_text = response.text
                if not raw_text:
                    raise GeminiServiceError("Empty response received from Gemini API.")

                parsed_json = json.loads(raw_text)
                validated_output = GeminiAnalysisOutput.model_validate(parsed_json)
                return validated_output

            except (json.JSONDecodeError, ValidationError) as parse_exc:
                # Do NOT retry malformed outputs or schema validation failures
                clean_err = mask_sensitive_data(str(parse_exc))
                logger.error(f"Failed to parse or validate Gemini response: {clean_err}")
                raise GeminiServiceError(f"Malformed intelligence output returned by Gemini API: {clean_err}")

            except Exception as exc:
                if attempt < max_retries and is_transient_error(exc):
                    backoff = (2 ** attempt) * 1.0  # 1.0s, 2.0s
                    clean_err = mask_sensitive_data(str(exc))
                    logger.warning(
                        f"Transient Gemini API error on attempt {attempt + 1}/{max_retries + 1}: {clean_err}. "
                        f"Retrying in {backoff}s..."
                    )
                    time.sleep(backoff)
                    continue
                else:
                    clean_err = mask_sensitive_data(str(exc))
                    logger.error(f"Gemini API invocation error: {clean_err}")
                    raise GeminiServiceError(f"Gemini API analysis failed: {clean_err}")

    except GeminiServiceError:
        raise
    except Exception as e:
        clean_err = mask_sensitive_data(str(e))
        logger.error(f"Unexpected error initializing Gemini client: {clean_err}")
        raise GeminiServiceError(f"Gemini API analysis failed: {clean_err}")
