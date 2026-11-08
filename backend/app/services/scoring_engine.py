"""
Resume Compatibility Scoring Engine.

Deterministic, candidate-type-aware scoring logic:
- Computes Section Completeness Score (0-100)
- Computes Impact & Action Score (0-100)
- Computes Formatting & Structure Score (0-100)
- Computes overall Resume Compatibility Score (0-100)
- Generates detailed, transparent explanations with weights and factor subscores.
- Candidate-type aware: student, fresher, experienced.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Set, Tuple

from app.models.candidate import CandidateType


ACTION_VERBS: Set[str] = {
    "accelerated", "accomplished", "achieved", "acquired", "adapted", "administered",
    "advised", "analyzed", "architected", "arranged", "assembled", "assessed",
    "audited", "automated", "boosted", "briefed", "budgeted", "built", "calculated",
    "cataloged", "championed", "collaborated", "compiled", "composed", "computed",
    "conceptualized", "conducted", "consolidated", "constructed", "consulted",
    "converted", "coordinated", "counseled", "created", "customized", "debugged",
    "decreased", "defined", "delegated", "delivered", "demonstrated", "deployed",
    "designed", "developed", "devised", "diagnosed", "directed", "discovered",
    "dispatched", "drafted", "earned", "edited", "educated", "elevated", "engineered",
    "enhanced", "enlarged", "established", "estimated", "evaluated", "examined",
    "executed", "expanded", "expedited", "fabricated", "facilitated", "forecasted",
    "formulated", "fostered", "founded", "generated", "governed", "guided",
    "handled", "headed", "identified", "illustrated", "implemented", "improved",
    "improvised", "increased", "influenced", "initiated", "innovated", "inspected",
    "instituted", "instructed", "integrated", "intensified", "interpreted",
    "introduced", "invented", "investigated", "launched", "lead", "led", "leveraged",
    "maintained", "managed", "maximized", "measured", "mediated", "mentored",
    "migrated", "minimized", "modeled", "moderated", "modernized", "modified",
    "monitored", "motivated", "navigated", "negotiated", "obtained", "operated",
    "optimized", "orchestrated", "organized", "originated", "overhauled", "oversaw",
    "performed", "piloted", "pioneered", "planned", "prepared", "presented",
    "prioritized", "produced", "programmed", "promoted", "proposed", "published",
    "quantified", "streamlined", "rebuilt", "recommended", "reconciled", "recorded",
    "recruited", "redesigned", "reduced", "refactored", "refined", "reformed",
    "regulated", "rehabilitated", "reinforced", "reorganized", "repaired", "replaced",
    "researched", "resolved", "restructured", "retrieved", "revamped", "reviewed",
    "revised", "revitalized", "saved", "scaled", "scheduled", "screened", "secured",
    "selected", "simplified", "simulated", "solved", "spearheaded", "standardized",
    "stimulated", "strategized", "streamlined", "strengthened", "structured",
    "supervised", "supported", "surpassed", "synthesized", "systematized", "tabulated",
    "targeted", "taught", "tested", "tracked", "trained", "transformed", "translated",
    "troubleshot", "unified", "upgraded", "utilized", "validated", "verified",
}

WEAK_PHRASES: List[Tuple[str, str]] = [
    (r"\bresponsible for\b", "Replace passive 'responsible for' with a direct action verb (e.g., 'Directed', 'Implemented')"),
    (r"\bduties included\b", "Replace 'duties included' with concrete action verbs describing what you actually delivered"),
    (r"\bhelped with\b", "Replace vague 'helped with' with specific contribution verbs like 'Collaborated on' or 'Co-engineered'"),
    (r"\bworked on\b", "Replace generic 'worked on' with precise action verbs (e.g., 'Engineered', 'Optimized', 'Designed')"),
    (r"\bassisted in\b", "Clarify your specific contribution instead of 'assisted in'"),
    (r"\bteam player\b", "Demonstrate collaboration through team accomplishments rather than the cliché phrase 'team player'"),
    (r"\bhard-?working\b", "Showcase your work ethic with tangible results rather than describing yourself as 'hard-working'"),
    (r"\bresults-?driven\b", "Highlight specific metrics and business results rather than using the generic buzzword 'results-driven'"),
]

SECTION_PATTERNS: Dict[str, List[str]] = {
    "Summary": [
        r"(?im)^(?:professional\s+summary|summary|profile|career\s+profile|executive\s+summary|about\s+me|career\s+objective|objective)\b",
    ],
    "Experience": [
        r"(?im)^(?:work\s+experience|professional\s+experience|employment\s+history|experience|career\s+history|relevant\s+experience)\b",
    ],
    "Education": [
        r"(?im)^(?:education|academic\s+background|academic\s+qualifications|educational\s+background|academics)\b",
    ],
    "Skills": [
        r"(?im)^(?:technical\s+skills|skills|core\s+competencies|technologies|tools\s+&?\s*technologies|key\s+skills|skill\s+set|technical\s+proficiencies)\b",
    ],
    "Projects": [
        r"(?im)^(?:projects|academic\s+projects|personal\s+projects|key\s+projects|selected\s+projects|technical\s+projects)\b",
    ],
    "Certifications": [
        r"(?im)^(?:certifications|licenses\s+&?\s*certifications|certifications\s+&?\s*licenses|certificates|accreditations|courses\s+&?\s*certifications)\b",
    ],
    "Awards & Achievements": [
        r"(?im)^(?:honors\s+&?\s*awards|awards|achievements|key\s+achievements|honors|accomplishments)\b",
    ],
}

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
LINK_REGEX = re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:linkedin\.com\/(?:in|pub)\/[a-zA-Z0-9_-]+|github\.com\/[a-zA-Z0-9_-]+|gitlab\.com\/[a-zA-Z0-9_-]+|[a-zA-Z0-9_-]+\.(?:dev|io|me|portfolio))\b", re.IGNORECASE)

METRIC_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b\d+(?:\.\d+)?%"),  # Percentages (e.g. 25%, 3.5%)
    re.compile(r"(?:\$|€|£|₹|Rs\.?)\s*\d+(?:,\d{3})*(?:\.\d+)?\s*(?:[kmb]|million|billion)?\b", re.IGNORECASE),  # Currency
    re.compile(r"\b\d+(?:\.\d+)?x\b", re.IGNORECASE),  # Multipliers (e.g. 2x, 10x)
    re.compile(r"\b\d+(?:,\d{3})*\+?\s*(?:users|clients|customers|requests|qps|endpoints|transactions|downloads|stars|prs|queries|engineers|team\s+members|developers|students|hours|ms|seconds|minutes|days|weeks|months|percent)\b", re.IGNORECASE),
]


@dataclass
class FactorResult:
    name: str
    score: int
    weight: float
    explanation: str


@dataclass
class DeterministicScoreResult:
    compatibility_score: int
    section_score: int
    impact_score: int
    formatting_score: int
    identified_sections: List[str]
    scoring_breakdown: Dict[str, Any]
    detected_verbs_count: int
    detected_metrics_count: int
    word_count: int
    has_email: bool
    has_phone: bool
    has_links: bool


def detect_sections(text: str) -> List[str]:
    """Detects recognized section headings present in the resume text."""
    detected = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for section_name, patterns in SECTION_PATTERNS.items():
        found = False
        for line in lines:
            # Check if line looks like a header (short, matches section keyword)
            if len(line) <= 60:
                clean_line = line.strip(": -#*=")
                for pat in patterns:
                    if re.search(pat, clean_line):
                        detected.append(section_name)
                        found = True
                        break
            if found:
                break
    return detected


def evaluate_contact_info(text: str) -> Tuple[bool, bool, bool, int, List[FactorResult]]:
    """Evaluates presence of contact information."""
    has_email = bool(EMAIL_REGEX.search(text))
    has_phone = bool(PHONE_REGEX.search(text))
    has_links = bool(LINK_REGEX.search(text))

    factors: List[FactorResult] = []

    # Email
    email_score = 100 if has_email else 0
    factors.append(FactorResult(
        name="Email Address",
        score=email_score,
        weight=0.35,
        explanation="Valid professional email found" if has_email else "No professional email address detected",
    ))

    # Phone
    phone_score = 100 if has_phone else 0
    factors.append(FactorResult(
        name="Phone Number",
        score=phone_score,
        weight=0.35,
        explanation="Contact phone number detected" if has_phone else "No contact phone number detected",
    ))

    # Professional links (LinkedIn / GitHub / Portfolio)
    link_score = 100 if has_links else 30
    factors.append(FactorResult(
        name="Professional Links",
        score=link_score,
        weight=0.30,
        explanation="LinkedIn, GitHub or portfolio link found" if has_links else "No LinkedIn or GitHub profile link detected",
    ))

    contact_score = round(email_score * 0.35 + phone_score * 0.35 + link_score * 0.30)
    return has_email, has_phone, has_links, contact_score, factors


def evaluate_sections(
    detected_sections: List[str],
    has_contact: bool,
    candidate_type: CandidateType,
) -> Tuple[int, List[FactorResult]]:
    """Evaluates section completeness tailored to the candidate's experience level."""
    factors: List[FactorResult] = []

    # Setup weights and expectations per candidate type
    if candidate_type == CandidateType.student:
        # Students: Education and Projects are critical, Experience is optional bonus
        requirements = [
            ("Contact Information", has_contact, 0.20, "Contact details (email, phone, links)"),
            ("Education", "Education" in detected_sections, 0.30, "Academic degrees, coursework, GPA/honors"),
            ("Skills", "Skills" in detected_sections, 0.25, "Technical skills, tools, programming languages"),
            ("Projects", "Projects" in detected_sections, 0.25, "Academic or independent technical projects"),
        ]
        # Bonus for experience or certifications
        bonus = 0
        if "Experience" in detected_sections:
            bonus += 10
        if "Certifications" in detected_sections or "Awards & Achievements" in detected_sections:
            bonus += 5

    elif candidate_type == CandidateType.fresher:
        # Freshers: Balanced expectation of Projects, Skills, Education, and Internships
        requirements = [
            ("Contact Information", has_contact, 0.20, "Contact details (email, phone, links)"),
            ("Education", "Education" in detected_sections, 0.25, "Degree, institution, graduation year"),
            ("Skills", "Skills" in detected_sections, 0.25, "Technical stack, tools, frameworks"),
            ("Projects", "Projects" in detected_sections, 0.20, "Portfolio projects demonstrating applied knowledge"),
            ("Experience / Internships", "Experience" in detected_sections, 0.10, "Internship or volunteer experience"),
        ]
        bonus = 0
        if "Certifications" in detected_sections or "Awards & Achievements" in detected_sections:
            bonus += 5
        if "Summary" in detected_sections:
            bonus += 5

    else:
        # Experienced: High emphasis on Work Experience, Skills, Summary, followed by Education
        requirements = [
            ("Contact Information", has_contact, 0.15, "Contact details (email, phone, links)"),
            ("Work Experience", "Experience" in detected_sections, 0.35, "Chronological professional work history"),
            ("Skills", "Skills" in detected_sections, 0.25, "Core competencies, frameworks, systems"),
            ("Education", "Education" in detected_sections, 0.15, "Academic degrees and formal background"),
            ("Professional Summary", "Summary" in detected_sections, 0.10, "Executive overview of career profile"),
        ]
        bonus = 0
        if "Projects" in detected_sections:
            bonus += 5
        if "Certifications" in detected_sections or "Awards & Achievements" in detected_sections:
            bonus += 5

    total_score = 0.0
    for name, is_present, weight, description in requirements:
        score = 100 if is_present else 0
        total_score += score * weight
        factors.append(FactorResult(
            name=name,
            score=score,
            weight=weight,
            explanation=f"{name} detected" if is_present else f"Missing {name.lower()} section ({description})",
        ))

    final_score = min(100, round(total_score + bonus))
    return final_score, factors


def extract_action_verbs(text: str) -> Tuple[int, List[str]]:
    """Identifies action verbs used in resume text."""
    words = re.findall(r"\b[A-Za-z]+(?:-[A-Za-z]+)?\b", text.lower())
    found_verbs = [w for w in words if w in ACTION_VERBS]
    unique_verbs = list(dict.fromkeys(found_verbs))
    return len(found_verbs), unique_verbs


def extract_metrics(text: str) -> Tuple[int, List[str]]:
    """Identifies measurable impact metrics (percentages, numbers with units, currency)."""
    detected_metrics: List[str] = []
    for pat in METRIC_PATTERNS:
        matches = pat.findall(text)
        detected_metrics.extend([m.strip() for m in matches if isinstance(m, str)])
    return len(detected_metrics), detected_metrics


def evaluate_impact(
    text: str,
    candidate_type: CandidateType,
) -> Tuple[int, int, int, List[FactorResult]]:
    """
    Evaluates impact, action verb usage, and quantifiable outcomes.
    Context-aware: does not unfairly penalize students for missing multi-million dollar metrics.
    """
    verb_count, unique_verbs = extract_action_verbs(text)
    metric_count, metrics_found = extract_metrics(text)

    # Detect weak phrases
    weak_findings: List[str] = []
    for pat, explanation in WEAK_PHRASES:
        if re.search(pat, text, re.IGNORECASE):
            weak_findings.append(explanation)

    factors: List[FactorResult] = []

    # 1. Action Verbs Factor
    # Target verb count depends on candidate type
    target_verbs = 5 if candidate_type == CandidateType.student else (8 if candidate_type == CandidateType.fresher else 12)
    verb_ratio = min(1.0, len(unique_verbs) / max(1, target_verbs))
    verb_score = round(verb_ratio * 100)
    verb_explanation = (
        f"Strong action orientation with {len(unique_verbs)} distinct action verbs (e.g. {', '.join(unique_verbs[:4])})"
        if len(unique_verbs) >= target_verbs
        else f"Found {len(unique_verbs)} distinct action verbs; aim for at least {target_verbs} active verbs"
    )
    factors.append(FactorResult(
        name="Action Verb Strength",
        score=verb_score,
        weight=0.45 if candidate_type == CandidateType.student else (0.40 if candidate_type == CandidateType.fresher else 0.35),
        explanation=verb_explanation,
    ))

    # 2. Measurable Metrics Factor
    # Context-aware: students only need 1-2 metrics for a solid score; experienced need 5+
    if candidate_type == CandidateType.student:
        if metric_count >= 3:
            metric_score = 100
            metric_exp = f"Excellent quantification for a student profile ({metric_count} measurable outcomes detected)"
        elif metric_count >= 1:
            metric_score = 80
            metric_exp = f"Good start on quantification ({metric_count} metrics found). Adding project benchmarks will improve impact"
        else:
            metric_score = 60  # Mild penalty only for student!
            metric_exp = "No quantifiable metrics found in project descriptions (consider adding team size, test coverage, or speedup percentages)"
        metric_weight = 0.30
    elif candidate_type == CandidateType.fresher:
        if metric_count >= 4:
            metric_score = 100
            metric_exp = f"Impressive measurable outcomes ({metric_count} metrics identified)"
        elif metric_count >= 2:
            metric_score = 80
            metric_exp = f"Satisfactory quantification ({metric_count} metrics identified). Deepen project outcome statistics"
        elif metric_count == 1:
            metric_score = 65
            metric_exp = "Only 1 quantifiable metric detected. Quantify achievements (users, performance gain, efficiency)"
        else:
            metric_score = 45
            metric_exp = "No quantifiable achievements found. Quantify project and internship accomplishments with concrete numbers"
        metric_weight = 0.40
    else:  # Experienced
        if metric_count >= 6:
            metric_score = 100
            metric_exp = f"Superb metric-driven resume ({metric_count} quantifiable results detected)"
        elif metric_count >= 3:
            metric_score = 80
            metric_exp = f"Solid quantification ({metric_count} metrics found). Include more business impact and scale figures"
        elif metric_count >= 1:
            metric_score = 55
            metric_exp = f"Limited quantification ({metric_count} metric found) for an experienced professional. Add revenue, latency, team or system scale"
        else:
            metric_score = 35
            metric_exp = "Lacks measurable business or technical outcomes. Experienced roles demand quantified achievements (% improved, scale handled, $ saved)"
        metric_weight = 0.50

    factors.append(FactorResult(
        name="Measurable Metrics & Impact",
        score=metric_score,
        weight=metric_weight,
        explanation=metric_exp,
    ))

    # 3. Tone & Precision (Lack of weak/passive phrases)
    weak_phrase_penalty = min(40, len(weak_findings) * 10)
    tone_score = max(20, 100 - weak_phrase_penalty)
    tone_weight = 1.0 - (factors[0].weight + factors[1].weight)
    tone_exp = (
        "Strong active tone without clichés or passive phrasing"
        if not weak_findings
        else f"Identified {len(weak_findings)} passive or cliché phrases (e.g., '{weak_findings[0]}')"
    )
    factors.append(FactorResult(
        name="Clarity & Precision",
        score=tone_score,
        weight=round(tone_weight, 2),
        explanation=tone_exp,
    ))

    impact_score = round(sum(f.score * f.weight for f in factors))
    return impact_score, len(unique_verbs), metric_count, factors


def evaluate_formatting(
    text: str,
    has_email: bool,
    has_phone: bool,
    has_links: bool,
    candidate_type: CandidateType,
) -> Tuple[int, int, List[FactorResult]]:
    """Evaluates formatting, word count suitability, and layout readability."""
    words = text.split()
    word_count = len(words)
    factors: List[FactorResult] = []

    # 1. Word Count Suitability
    if candidate_type == CandidateType.student:
        target_min, target_max = 150, 650
    elif candidate_type == CandidateType.fresher:
        target_min, target_max = 200, 800
    else:
        target_min, target_max = 250, 1100

    if target_min <= word_count <= target_max:
        length_score = 100
        length_exp = f"Word count ({word_count} words) is well-suited for a {candidate_type.value} resume (target: {target_min}-{target_max})"
    elif word_count < target_min:
        shortfall = target_min - word_count
        length_score = max(40, 100 - int((shortfall / target_min) * 60))
        length_exp = f"Resume is brief ({word_count} words; target {target_min}-{target_max}). Consider expanding project details and achievements"
    else:
        excess = word_count - target_max
        length_score = max(50, 100 - int((excess / target_max) * 50))
        length_exp = f"Resume is lengthy ({word_count} words; target {target_min}-{target_max}). Tighten phrasing to improve reader retention"

    factors.append(FactorResult(
        name="Resume Length & Density",
        score=length_score,
        weight=0.35,
        explanation=length_exp,
    ))

    # 2. Structure & Bullet Points
    bullet_indicators = [line for line in text.splitlines() if re.match(r"^\s*[\u2022\u25E6\u2023\u25AA\-\*]\s+", line)]
    bullet_count = len(bullet_indicators)
    if bullet_count >= 6:
        bullet_score = 100
        bullet_exp = f"Excellent use of bullet points ({bullet_count} bullets) for readability"
    elif bullet_count >= 3:
        bullet_score = 80
        bullet_exp = f"Acceptable use of bullets ({bullet_count} bullets). Convert remaining paragraph text into scannable bullets"
    elif bullet_count > 0:
        bullet_score = 60
        bullet_exp = f"Low bullet count ({bullet_count}). Use bulleted lists under experience and projects for easier ATS parsing"
    else:
        bullet_score = 40
        bullet_exp = "No standard bullet points detected. ATS scanners and recruiters strongly favor bulleted accomplishment statements"


    factors.append(FactorResult(
        name="Scannability & Bulleted Structure",
        score=bullet_score,
        weight=0.35,
        explanation=bullet_exp,
    ))

    # 3. Contact & Header Organization
    header_items = sum([has_email, has_phone, has_links])
    if header_items == 3:
        header_score = 100
        header_exp = "Complete header with email, phone, and professional link"
    elif header_items == 2:
        header_score = 75
        header_exp = "Good contact info, but missing either phone, email, or a portfolio/LinkedIn link"
    elif header_items == 1:
        header_score = 50
        header_exp = "Minimal contact details found. Ensure phone, email, and LinkedIn are prominently featured"
    else:
        header_score = 15
        header_exp = "Critical contact information missing from resume header"

    factors.append(FactorResult(
        name="Header & Contact Formatting",
        score=header_score,
        weight=0.30,
        explanation=header_exp,
    ))

    formatting_score = round(sum(f.score * f.weight for f in factors))
    return formatting_score, word_count, factors


def calculate_compatibility_score(
    text: str,
    candidate_type: CandidateType = CandidateType.experienced,
) -> DeterministicScoreResult:
    """
    Main entry point for candidate-type-aware deterministic resume scoring.
    Produces:
    - Section Completeness Score (0-100)
    - Impact & Metrics Score (0-100)
    - Formatting & Layout Score (0-100)
    - Resume Compatibility Score (0-100)
    - Detailed scoring breakdown
    """
    if not text or not text.strip():
        return DeterministicScoreResult(
            compatibility_score=0,
            section_score=0,
            impact_score=0,
            formatting_score=0,
            identified_sections=[],
            scoring_breakdown={
                "candidate_type": candidate_type.value,
                "notes": ["No readable text extracted from document."],
            },
            detected_verbs_count=0,
            detected_metrics_count=0,
            word_count=0,
            has_email=False,
            has_phone=False,
            has_links=False,
        )

    # 1. Identify sections & contact info
    identified_sections = detect_sections(text)
    has_email, has_phone, has_links, contact_score, contact_factors = evaluate_contact_info(text)
    has_contact = (has_email or has_phone)

    # 2. Evaluate sections
    section_score, section_factors = evaluate_sections(identified_sections, has_contact, candidate_type)

    # 3. Evaluate impact & verbs
    impact_score, verbs_count, metrics_count, impact_factors = evaluate_impact(text, candidate_type)

    # 4. Evaluate formatting & readability
    formatting_score, word_count, formatting_factors = evaluate_formatting(
        text, has_email, has_phone, has_links, candidate_type
    )

    # 5. Composite Resume Compatibility Score weights by candidate type
    if candidate_type == CandidateType.student:
        w_section = 0.45
        w_impact = 0.25
        w_format = 0.30
    elif candidate_type == CandidateType.fresher:
        w_section = 0.40
        w_impact = 0.35
        w_format = 0.25
    else:  # Experienced
        w_section = 0.30
        w_impact = 0.45
        w_format = 0.25

    raw_compatibility = (
        section_score * w_section
        + impact_score * w_impact
        + formatting_score * w_format
    )
    compatibility_score = max(0, min(100, round(raw_compatibility)))

    # Structure detailed breakdown dictionary
    breakdown: Dict[str, Any] = {
        "candidate_type": candidate_type.value,
        "weights": {
            "section_weight": w_section,
            "impact_weight": w_impact,
            "formatting_weight": w_format,
        },
        "section_factors": [
            {"name": f.name, "score": f.score, "weight": f.weight, "explanation": f.explanation}
            for f in section_factors
        ],
        "impact_factors": [
            {"name": f.name, "score": f.score, "weight": f.weight, "explanation": f.explanation}
            for f in impact_factors
        ],
        "formatting_factors": [
            {"name": f.name, "score": f.score, "weight": f.weight, "explanation": f.explanation}
            for f in formatting_factors
        ],
        "metrics_summary": {
            "word_count": word_count,
            "verbs_count": verbs_count,
            "metrics_count": metrics_count,
            "has_email": has_email,
            "has_phone": has_phone,
            "has_links": has_links,
            "identified_sections": identified_sections,
        },
    }

    return DeterministicScoreResult(
        compatibility_score=compatibility_score,
        section_score=section_score,
        impact_score=impact_score,
        formatting_score=formatting_score,
        identified_sections=identified_sections,
        scoring_breakdown=breakdown,
        detected_verbs_count=verbs_count,
        detected_metrics_count=metrics_count,
        word_count=word_count,
        has_email=has_email,
        has_phone=has_phone,
        has_links=has_links,
    )
