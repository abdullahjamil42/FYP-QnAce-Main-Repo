"""
Q&Ace — Question Bank.

Loads DSA questions from dsa_final_a_plus.json and generates per-role
question sets for Quick (~7 Qs) and Extensive (~15 Qs) interview formats.
"""

from __future__ import annotations

import json
import logging
import random
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("qace.question_bank")

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # → LLM/
_DSA_FILE = _REPO_ROOT / "dsa_final_a_plus.json"

_dsa_questions: list[dict[str, Any]] | None = None

ROLE_SPECIFIC_QUESTIONS: dict[str, list[str]] = {
    "cloud_computing": [
        "How would you design a highly available multi-region deployment on AWS or Azure?",
        "Explain the trade-offs between serverless and containerized architectures.",
        "How do you handle secrets management and IAM policies in a cloud-native environment?",
        "Describe your approach to cost optimization in a cloud infrastructure.",
        "How would you set up a CI/CD pipeline with blue-green deployments?",
        "Explain how you would design a disaster recovery strategy for a cloud application.",
        "What is your approach to monitoring and observability in distributed cloud systems?",
        "How do you handle auto-scaling for unpredictable traffic patterns?",
        "Describe the networking considerations when designing a multi-VPC architecture.",
        "How would you migrate a monolithic on-prem application to microservices in the cloud?",
    ],
    "ai_engineering": [
        "Walk me through your approach to deploying a machine learning model to production.",
        "How do you handle model versioning and A/B testing in an ML pipeline?",
        "Explain the trade-offs between batch and real-time inference serving.",
        "How do you detect and mitigate model drift in production?",
        "Describe your approach to feature engineering and feature stores.",
        "How would you design a data pipeline for training at scale?",
        "What MLOps practices do you consider essential for production ML systems?",
        "How do you handle GPU resource allocation for training and inference?",
        "Explain how you would build a RAG system for a domain-specific application.",
        "How do you evaluate model performance beyond accuracy metrics?",
    ],
    "data_scientist": [
        "How do you approach a new dataset — what is your exploratory data analysis workflow?",
        "Explain the difference between correlation and causation with a real-world example.",
        "How do you handle class imbalance in a classification problem?",
        "Describe your approach to feature selection and dimensionality reduction.",
        "How do you design and interpret A/B tests?",
        "Walk me through how you would build a recommendation system from scratch.",
        "How do you communicate statistical findings to non-technical stakeholders?",
        "Explain the bias-variance trade-off and how it influences model selection.",
        "How do you handle missing data in your analysis pipeline?",
        "Describe a situation where your model failed and what you learned from it.",
    ],
    "web_engineering": [
        "How would you optimize the performance of a React application with slow renders?",
        "Explain the trade-offs between SSR, SSG, and CSR in a Next.js application.",
        "How do you handle authentication and session management in a web app?",
        "Describe your approach to designing a responsive and accessible UI.",
        "How do you structure a REST API for maintainability and versioning?",
        "Explain how you would implement real-time features using WebSockets.",
        "How do you handle state management in a complex single-page application?",
        "Describe your approach to frontend testing — unit, integration, and e2e.",
        "How would you design a CDN caching strategy for a content-heavy site?",
        "How do you handle API error states and provide good user experience?",
    ],
    "software_engineer": [
        "Explain a complex system you designed. What were the core components and trade-offs?",
        "Tell me about a production bug you diagnosed. How did you isolate and fix it?",
        "How do you design a REST API for reliability and versioning?",
        "Describe a time you improved application performance. What metrics moved?",
        "How would you design caching for a high-traffic read-heavy service?",
        "What testing strategy do you use across unit, integration, and end-to-end tests?",
        "Describe a difficult code review discussion and how you resolved it.",
        "If you had to scale this app to 10x users, what would you change first?",
        "How do you approach technical debt — when do you refactor vs ship?",
        "Walk me through how you would design a rate limiter from scratch.",
    ],
}

BEHAVIORAL_QUESTIONS: list[str] = [
    "Tell me about yourself and your professional background.",
    "Describe a time you had a conflict with a teammate. How did you resolve it?",
    "Give me an example of a project where you led or took initiative.",
    "Tell me about a time you failed at something. What did you learn from it?",
    "How do you prioritize tasks when everything feels urgent?",
    "Describe a situation where you had to learn something new quickly under pressure.",
    "What motivates you in your work, and what kind of team culture do you thrive in?",
    "Tell me about a time you received critical feedback. How did you respond?",
]

CLOSING_QUESTIONS: list[str] = [
    "What are your salary expectations for this role?",
    "Do you have any questions for us about the role or the team?",
    "When would you be available to start if you were offered this position?",
]


def _load_dsa_questions() -> list[dict[str, Any]]:
    global _dsa_questions
    if _dsa_questions is not None:
        return _dsa_questions

    if not _DSA_FILE.exists():
        logger.warning("DSA question file not found at %s", _DSA_FILE)
        _dsa_questions = []
        return _dsa_questions

    try:
        with open(_DSA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            _dsa_questions = data
            logger.info("Loaded %d DSA questions from %s", len(data), _DSA_FILE.name)
        else:
            logger.warning("DSA file is not a JSON array")
            _dsa_questions = []
    except Exception as exc:
        logger.warning("Failed to load DSA questions: %s", exc)
        _dsa_questions = []

    return _dsa_questions


def _format_dsa_question(q: dict[str, Any]) -> dict[str, str]:
    """Format a DSA entry into an interview question dict."""
    return {
        "text": (
            f"Coding question: {q.get('title', 'Unknown')}. "
            f"{q.get('problem_description', '')} "
            f"Please explain your approach and walk through your solution."
        ),
        "type": "dsa",
        "difficulty": q.get("difficulty", "Medium"),
        "category": q.get("category", "General"),
        "title": q.get("title", ""),
        "ideal_approach": q.get("optimal_approach", "")[:500],
        "python_code": q.get("python_code", ""),
        "time_complexity": q.get("time_complexity", ""),
        "space_complexity": q.get("space_complexity", ""),
    }


def _format_role_question(text: str, role: str) -> dict[str, str]:
    """Format a role-specific question into an interview question dict."""
    return {
        "text": text,
        "type": "role_specific",
        "difficulty": "Medium",
        "category": role,
        "title": "",
        "ideal_approach": "",
        "python_code": "",
        "time_complexity": "",
        "space_complexity": "",
    }


def _format_behavioral_question(text: str) -> dict[str, str]:
    """Format a behavioral question into an interview question dict."""
    return {
        "text": text,
        "type": "behavioral",
        "difficulty": "Easy",
        "category": "behavioral",
        "title": "",
        "ideal_approach": "",
        "python_code": "",
        "time_complexity": "",
        "space_complexity": "",
    }


def _format_closing_question(text: str) -> dict[str, str]:
    """Format a closing question into an interview question dict."""
    return {
        "text": text,
        "type": "closing",
        "difficulty": "Easy",
        "category": "closing",
        "title": "",
        "ideal_approach": "",
        "python_code": "",
        "time_complexity": "",
        "space_complexity": "",
    }


def _format_cv_question(text: str, role: str) -> dict[str, str]:
    return {
        "text": text,
        "type": "cv_personalized",
        "difficulty": "Medium",
        "category": role,
        "title": "",
        "ideal_approach": "",
        "python_code": "",
        "time_complexity": "",
        "space_complexity": "",
    }


def _adapt_question_to_cv(text: str, cv: Any) -> str:
    """Lightly personalise a templated question by injecting CV details.

    Replaces generic phrases like 'a system you built' / 'a project you worked on'
    with the candidate's actual first project name when available.
    """
    if cv is None or getattr(cv, "is_empty", lambda: True)():
        return text
    projects = getattr(cv, "projects", None) or []
    if not projects:
        return text
    first = projects[0]
    name = (first.get("name") or "").strip() if isinstance(first, dict) else ""
    if not name:
        return text
    patterns = [
        (r"\ba (?:system|service|app(?:lication)?|project) you (?:built|designed|worked on|shipped)\b",
         f"{name}"),
        (r"\ba recent project\b", f"{name}"),
    ]
    adapted = text
    for pat, repl in patterns:
        adapted = re.sub(pat, repl, adapted, count=1, flags=re.IGNORECASE)
    return adapted


def generate_question_set(
    job_role: str,
    interview_type: str,
    seed: int | None = None,
    cv: Any | None = None,
    cv_questions: list[str] | None = None,
) -> list[dict[str, str]]:
    """Generate a question set based on job role and interview type.

    Returns a list of question dicts with 'text', 'type', 'difficulty', etc.
    Order: behavioral → technical (role-specific + DSA shuffled) → closing.

    Quick:     1 behavioral + 3 role + 4 DSA + 1 closing = ~9
    Extensive: 2 behavioral + 6 role + 9 DSA + 2 closing = ~19
    """
    rng = random.Random(seed)
    all_dsa = _load_dsa_questions()
    role_key = job_role if job_role in ROLE_SPECIFIC_QUESTIONS else "software_engineer"
    role_questions = list(ROLE_SPECIFIC_QUESTIONS[role_key])
    behavioral_pool = list(BEHAVIORAL_QUESTIONS)
    closing_pool = list(CLOSING_QUESTIONS)

    has_cv_questions = bool(cv_questions)
    if interview_type == "quick":
        behavioral_count = 1
        role_count = 2 if has_cv_questions else 3
        dsa_count = 3 if has_cv_questions else 4
        closing_count = 1
        dsa_difficulties = {"Easy", "Medium"}
    else:
        behavioral_count = 2
        role_count = 4 if has_cv_questions else 6
        dsa_count = 7 if has_cv_questions else 9
        closing_count = 2
        dsa_difficulties = {"Medium", "Hard"}

    # Behavioral (front)
    rng.shuffle(behavioral_pool)
    selected_behavioral = [_format_behavioral_question(q) for q in behavioral_pool[:behavioral_count]]

    # Technical (middle, shuffled together)
    rng.shuffle(role_questions)
    selected_role = [
        _format_role_question(_adapt_question_to_cv(q, cv), role_key)
        for q in role_questions[:role_count]
    ]

    filtered_dsa = [q for q in all_dsa if q.get("difficulty", "") in dsa_difficulties]
    if not filtered_dsa:
        filtered_dsa = all_dsa

    rng.shuffle(filtered_dsa)
    selected_dsa = [_format_dsa_question(q) for q in filtered_dsa[:dsa_count]]

    # CV-personalised questions (if provided) sit alongside role questions
    selected_cv = [_format_cv_question(q, role_key) for q in (cv_questions or [])]

    technical = selected_role + selected_cv + selected_dsa
    rng.shuffle(technical)

    # Closing (end, never shuffled into the middle)
    rng.shuffle(closing_pool)
    selected_closing = [_format_closing_question(q) for q in closing_pool[:closing_count]]

    return selected_behavioral + technical + selected_closing
