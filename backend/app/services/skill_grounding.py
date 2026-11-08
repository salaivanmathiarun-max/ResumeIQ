"""
Skill Grounding and Verification Service.

Deterministically verifies candidate skills extracted by Gemini against the original resume text:
1. Explicit Skills: Verified directly or via strict aliases with boundary protection.
2. Contextual Skills: Verified via verbatim evidence excerpt matching and substantive relevance checks.
3. Anti-Collision Safeguards: Special boundary protections for short/ambiguous skill names (Go, C, R, TS).
4. Empty Category Dropping: Only verified skills are returned, dropping empty buckets.
5. Contract Preservation: Returns Dict[str, List[str]] to preserve the existing API contract.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)

# Curated alias dictionary: canonical display name -> list of aliases/synonyms
TECH_ALIASES: Dict[str, List[str]] = {
    # Programming Languages
    "python": ["python", "python3", "py"],
    "javascript": ["javascript", "js", "ecmascript", "es6", "es2015"],
    "typescript": ["typescript", "ts"],
    "golang": ["golang", "go"],
    "c++": ["c++", "cpp", "c++11", "c++14", "c++17", "c++20", "c++23"],
    "c#": ["c#", "csharp", "c sharp", ".net"],
    "java": ["java"],
    "rust": ["rust"],
    "ruby": ["ruby", "ruby on rails", "rails"],
    "php": ["php"],
    "swift": ["swift"],
    "kotlin": ["kotlin"],
    "dart": ["dart", "flutter"],
    "r": ["r programming", "rstudio", "r script"],
    "sql": ["sql", "structured query language"],

    # Frontend
    "react": ["react", "reactjs", "react.js"],
    "react native": ["react native", "react-native"],
    "vue": ["vue", "vuejs", "vue.js", "vue3"],
    "angular": ["angular", "angularjs"],
    "next.js": ["nextjs", "next.js", "next"],
    "nuxt.js": ["nuxtjs", "nuxt.js", "nuxt"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "tailwind css": ["tailwind", "tailwindcss", "tailwind css"],
    "bootstrap": ["bootstrap"],
    "sass": ["sass", "scss"],
    "redux": ["redux", "redux toolkit", "rtk"],
    "graphql": ["graphql", "apollo"],

    # Backend & APIs
    "fastapi": ["fastapi", "fast-api"],
    "django": ["django", "django rest framework", "drf"],
    "flask": ["flask"],
    "node.js": ["nodejs", "node.js", "node"],
    "express": ["express", "expressjs", "express.js"],
    "nest.js": ["nestjs", "nest.js"],
    "spring boot": ["spring boot", "springboot", "spring framework", "spring"],
    "asp.net": ["asp.net", "aspnet", ".net core", "dotnet"],
    "rest apis": ["rest api", "rest apis", "restful", "restful api", "rest endpoints", "restful services", "rest"],
    "grpc": ["grpc"],
    "websockets": ["websocket", "websockets", "socket.io"],

    # Databases & Caches
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql"],
    "sqlite": ["sqlite", "sqlite3"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search"],
    "cassandra": ["cassandra"],
    "dynamodb": ["dynamodb"],

    # DevOps, Cloud & Tools
    "docker": ["docker", "dockerfile", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "azure": ["azure", "microsoft azure"],
    "git": ["git", "github", "gitlab", "bitbucket"],
    "ci/cd": ["ci/cd", "ci-cd", "cicd", "continuous integration", "github actions", "gitlab ci", "jenkins"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "linux": ["linux", "unix", "ubuntu", "debian", "centos", "redhat", "bash", "shell"],

    # Data & ML
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow", "tf"],
    "keras": ["keras"],
    "spark": ["apache spark", "pyspark", "spark"],
    "kafka": ["apache kafka", "kafka"],
}

# Domain keyword indicators to evaluate substantive relevance of contextual excerpts
DOMAIN_INDICATORS: Dict[str, List[str]] = {
    "rest": ["api", "apis", "endpoint", "endpoints", "http", "crud", "fastapi", "express", "django", "flask", "service", "services", "route", "routes"],
    "docker": ["container", "containers", "containerized", "dockerfile", "compose", "image", "images"],
    "kubernetes": ["k8s", "cluster", "clusters", "pod", "pods", "deployment", "deployments", "helm"],
    "aws": ["ec2", "s3", "lambda", "rds", "cloudformation", "iam", "cloudwatch", "sqs", "sns", "dynamodb"],
    "gcp": ["bigquery", "cloud run", "gke", "cloud functions", "compute engine", "vertex"],
    "azure": ["blob storage", "azure functions", "aks", "cosmosdb", "app service"],
    "ci/cd": ["pipeline", "pipelines", "github actions", "jenkins", "gitlab ci", "automated deployment", "build"],
    "testing": ["test", "tests", "unit test", "integration test", "pytest", "jest", "mock", "cypress"],
    "state management": ["redux", "context api", "zustand", "mobx", "vuex", "pinia", "store"],
    "database": ["db", "schema", "table", "tables", "query", "queries", "sql", "nosql", "migration", "indexing", "postgres", "mysql", "mongo"],
    "caching": ["cache", "caching", "redis", "memcached", "ttl"],
    "microservices": ["services", "distributed", "event-driven", "grpc", "message queue", "kafka", "rabbitmq"],
    "optimization": ["performance", "latency", "benchmark", "speed", "profiling", "throughput", "bundle size"],
    "security": ["authentication", "authorization", "oauth", "jwt", "rbac", "encryption", "https"],
}

# Stop words to ignore when extracting substantive terms from skill names
STOP_WORDS: Set[str] = {
    "and", "or", "the", "in", "for", "of", "with", "to", "a", "an", "on", "by", "from", "&", "/"
}


def normalize_whitespace(text: str) -> str:
    """Collapses consecutive whitespace, tabs, and newlines into a single space."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _match_short_or_ambiguous_skill(skill_lower: str, resume_text: str) -> bool:
    """
    Carefully verifies short or ambiguous programming language names (Go, C, R, TS).
    Prevents false-positive substring matches on words like 'go', 'to go', 'algorithm',
    letter 'c', letter 'r', or arbitrary timestamps/acronyms.
    """
    if skill_lower in ("go", "golang"):
        # Match 'golang' case-insensitively
        if re.search(r"\bgolang\b", resume_text, re.IGNORECASE):
            return True
        # Match uppercase 'Go' in explicit programming/language list context
        # e.g., 'Go, Python', 'Python / Go', 'Go programming', 'Go developer'
        patterns = [
            r"\bGo\s+(?:programming|language|developer|backend|code|routines?|channels?)\b",
            r"\b(?:Python|Java|Rust|C\+\+|TypeScript|JS|Ruby|C#)\s*(?:,\s*|\/\s*|and\s+|\|\s*)Go\b",
            r"\bGo\s*(?:,\s*|\/\s*|and\s+|\|\s*)(?:Python|Java|Rust|C\+\+|TypeScript|JS|Ruby|C#)\b",
            r"(?i:\b(?:languages?|technical\s+skills?|skills?|tech\s+stack|technologies)\s*:[^\n]*\bGo\b)",
        ]
        return any(re.search(p, resume_text) for p in patterns)

    if skill_lower == "c":
        # Match single-letter 'C' only in explicit programming language context
        patterns = [
            r"\bC\s+(?:programming|language|developer)\b",
            r"\bC\s*(?:,\s*|\/\s*|and\s+|\|\s*)(?:C\+\+|C#|Java|Python|Assembly|Rust)\b",
            r"\b(?:C\+\+|C#|Java|Python|Assembly|Rust)\s*(?:,\s*|\/\s*|and\s+|\|\s*)C\b",
            r"(?i:\b(?:languages?|technical\s+skills?|skills?|technologies)\s*:[^\n]*\bC\b)",
        ]
        return any(re.search(p, resume_text) for p in patterns)

    if skill_lower == "r":
        # Match single-letter 'R' in statistics/language context
        patterns = [
            r"\bR\s+(?:programming|language|studio|script|scripts)\b",
            r"\bRStudio\b",
            r"\bR\s*(?:,\s*|\/\s*|and\s+|\|\s*)(?:Python|SQL|SAS|MATLAB|SPSS|Julia|Stata)\b",
            r"\b(?:Python|SQL|SAS|MATLAB|SPSS|Julia|Stata)\s*(?:,\s*|\/\s*|and\s+|\|\s*)R\b",
            r"(?i:\b(?:languages?|technical\s+skills?|skills?|technologies)\s*:[^\n]*\bR\b)",
        ]
        return any(re.search(p, resume_text) for p in patterns)

    if skill_lower == "ts":
        if re.search(r"\btypescript\b", resume_text, re.IGNORECASE):
            return True
        patterns = [
            r"\b(?:TS\/JS|JS\/TS|TS\s*,\s*JS|JS\s*,\s*TS|React\/TS)\b",
            r"(?i:\b(?:languages?|technical\s+skills?|skills?)\s*:[^\n]*\bTS\b)",
        ]
        return any(re.search(p, resume_text) for p in patterns)

    return False


def verify_explicit_skill(skill: str, resume_text: str) -> bool:
    """
    Conservatively checks if an explicit skill is directly named in the resume text.
    Uses strict word boundaries, tech aliases, and short-name safeguards.
    """
    if not skill or not resume_text:
        return False

    raw_skill = skill.strip()
    skill_lower = raw_skill.lower()

    # Short/ambiguous technology safeguards
    if skill_lower in ("go", "c", "r", "ts"):
        return _match_short_or_ambiguous_skill(skill_lower, resume_text)

    # Gather search variants (canonical name + aliases)
    variants = [raw_skill]
    if skill_lower in TECH_ALIASES:
        variants.extend(TECH_ALIASES[skill_lower])
    else:
        # Check reverse aliases (if skill matches an alias in TECH_ALIASES)
        for canon, aliases in TECH_ALIASES.items():
            if skill_lower == canon or skill_lower in aliases:
                variants.append(canon)
                variants.extend(aliases)
                break

    # Deduplicate variants while preserving order
    unique_variants: List[str] = []
    seen: Set[str] = set()
    for v in variants:
        vl = v.lower()
        if vl not in seen:
            seen.add(vl)
            unique_variants.append(v)

    # Check each variant against resume text
    for variant in unique_variants:
        vl = variant.lower()

        # Handle special short forms in alias list
        if vl in ("go", "c", "r", "ts"):
            if _match_short_or_ambiguous_skill(vl, resume_text):
                return True
            continue

        # Handle skills containing punctuation (+, #, ., /, -)
        has_special = any(ch in variant for ch in ["+", "#", ".", "/", "-"])
        if has_special:
            escaped = re.escape(variant)
            pattern = rf"(?:^|[\s,;/|([\]{{}}<>\n\r\t]){escaped}(?:$|[\s,;/|()[\]{{}}<>\n\r\t])"
            if re.search(pattern, resume_text, re.IGNORECASE):
                return True
        else:
            # Standard word boundary regex
            escaped = re.escape(variant)
            pattern = rf"\b{escaped}\b"
            if re.search(pattern, resume_text, re.IGNORECASE):
                return True

    return False


def check_substantive_support(skill: str, evidence: str) -> bool:
    """
    Evaluates whether an evidence snippet substantively supports the claimed skill.
    Requires at least one meaningful keyword, alias, or domain indicator in the snippet.
    """
    if not skill or not evidence:
        return False

    skill_lower = skill.strip().lower()
    evidence_lower = evidence.strip().lower()

    # 1. Direct match: skill name or any alias appears in the evidence
    if skill_lower in evidence_lower:
        return True

    if skill_lower in TECH_ALIASES:
        for alias in TECH_ALIASES[skill_lower]:
            if alias.lower() in evidence_lower:
                return True

    # 2. Domain indicators check
    for domain_key, indicators in DOMAIN_INDICATORS.items():
        if domain_key in skill_lower:
            if any(ind in evidence_lower for ind in indicators):
                return True

    # 3. Meaningful skill keyword check (non-stop words of len >= 3)
    skill_words = [
        w.strip() for w in re.split(r"[\s/,_-]+", skill_lower)
        if w.strip() and len(w.strip()) >= 3 and w.strip() not in STOP_WORDS
    ]
    for word in skill_words:
        if re.search(rf"\b{re.escape(word)}\b", evidence_lower):
            return True

    return False


def verify_contextual_skill(skill: str, evidence: str, resume_text: str) -> bool:
    """
    Verifies a contextual skill:
    1. Evidence must be at least 10 characters long.
    2. Evidence snippet must appear verbatim in the resume text (whitespace-normalized).
    3. Evidence snippet must substantively support the claimed skill.
    """
    if not skill or not evidence or not resume_text:
        return False

    clean_evidence = normalize_whitespace(evidence)
    if len(clean_evidence) < 10:
        logger.debug(f"Contextual evidence too short: '{clean_evidence}'")
        return False

    clean_resume = normalize_whitespace(resume_text)

    # 1. Verbatim check: snippet must exist in the resume text
    if clean_evidence.lower() not in clean_resume.lower():
        logger.debug(f"Contextual evidence not found verbatim in resume: '{clean_evidence[:50]}...'")
        return False

    # 2. Substantive relevance check
    if not check_substantive_support(skill, clean_evidence):
        logger.debug(f"Contextual evidence does not substantively support skill '{skill}': '{clean_evidence[:50]}...'")
        return False

    return True


def ground_and_filter_skills(
    raw_skills: Any,
    resume_text: str,
) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Gounds and filters skills extracted from Gemini against the original resume text.

    Args:
        raw_skills: SkillCategorizationSchema instance or dictionary with 'explicit' and 'contextual' keys.
        resume_text: Raw extracted resume text.

    Returns:
        A tuple of:
        - grounded_skills: Dict[str, List[str]] with empty categories dropped and valid verified skills.
        - rejected_skills: List[str] of skills rejected due to lack of evidence (for logging).
    """
    grounded_skills: Dict[str, List[str]] = {}
    rejected_skills: List[str] = []

    if not resume_text or not resume_text.strip():
        return grounded_skills, rejected_skills

    # Extract explicit and contextual buckets
    explicit_data: Dict[str, Any] = {}
    contextual_data: Dict[str, Any] = {}
    has_explicit_contextual_split = False

    if hasattr(raw_skills, "explicit") and hasattr(raw_skills, "contextual"):
        explicit_data = getattr(raw_skills, "explicit") or {}
        contextual_data = getattr(raw_skills, "contextual") or {}
        has_explicit_contextual_split = True
    elif isinstance(raw_skills, dict):
        if "explicit" in raw_skills or "contextual" in raw_skills:
            explicit_data = raw_skills.get("explicit") or {}
            contextual_data = raw_skills.get("contextual") or {}
            has_explicit_contextual_split = True
        else:
            # Fallback: legacy flat dict treated as explicit while preserving original category names
            explicit_data = raw_skills
            has_explicit_contextual_split = False

    # Process Explicit Skills
    if isinstance(explicit_data, dict):
        for category, skills in explicit_data.items():
            if not isinstance(skills, list):
                continue
            verified_in_cat: List[str] = []
            seen: Set[str] = set()
            for s in skills:
                skill_name = s.strip() if isinstance(s, str) else ""
                if not skill_name:
                    continue
                if verify_explicit_skill(skill_name, resume_text):
                    lower_name = skill_name.lower()
                    if lower_name not in seen:
                        seen.add(lower_name)
                        verified_in_cat.append(skill_name)
                else:
                    rejected_skills.append(f"{skill_name} (unsupported explicit in {category})")

            if verified_in_cat:
                if has_explicit_contextual_split:
                    cat_key = f"{category} (Explicit)" if not category.endswith("(Explicit)") else category
                else:
                    cat_key = category
                grounded_skills[cat_key] = verified_in_cat

    # Process Contextual Skills
    if isinstance(contextual_data, dict):
        for category, items in contextual_data.items():
            if not isinstance(items, list):
                continue
            verified_in_cat: List[str] = []
            seen: Set[str] = set()
            for item in items:
                skill_name = ""
                evidence_text = ""

                if isinstance(item, str):
                    skill_name = item.strip()
                    # A bare string without evidence is only accepted if it actually appears explicitly
                    if verify_explicit_skill(skill_name, resume_text):
                        lower_name = skill_name.lower()
                        if lower_name not in seen:
                            seen.add(lower_name)
                            verified_in_cat.append(skill_name)
                        continue
                    else:
                        rejected_skills.append(f"{skill_name} (contextual missing evidence excerpt)")
                        continue
                elif hasattr(item, "skill") and hasattr(item, "evidence"):
                    skill_name = getattr(item, "skill", "").strip()
                    evidence_text = getattr(item, "evidence", "").strip()
                elif isinstance(item, dict):
                    skill_name = str(item.get("skill", "")).strip()
                    evidence_text = str(item.get("evidence", "")).strip()

                if not skill_name or not evidence_text:
                    if skill_name:
                        rejected_skills.append(f"{skill_name} (empty evidence in {category})")
                    continue

                if verify_contextual_skill(skill_name, evidence_text, resume_text):
                    lower_name = skill_name.lower()
                    if lower_name not in seen:
                        seen.add(lower_name)
                        verified_in_cat.append(skill_name)
                else:
                    rejected_skills.append(f"{skill_name} (unverified contextual evidence in {category})")

            if verified_in_cat:
                cat_key = f"{category} (Contextual)" if not category.endswith("(Contextual)") else category
                grounded_skills[cat_key] = verified_in_cat

    return grounded_skills, rejected_skills

