from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass
class TopicConfig:
    topic_id: str
    title: str
    description: str
    num_questions: int
    easy_pct: int
    medium_pct: int
    hard_pct: int


@dataclass
class SubtopicConfig:
    topic_id: str
    name: str
    sort_order: int
    weight: float


def parse_schema(schema_path: Path) -> tuple[dict[str, TopicConfig], list[SubtopicConfig]]:
    text = schema_path.read_text(encoding="utf-8")

    topic_pattern = re.compile(
        r"\('([^']+)',\s*'([^']+)',\s*'([^']+)',\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)"
    )
    subtopic_pattern = re.compile(r"\('([^']+)',\s*'([^']+)',\s*(\d+),\s*([0-9.]+)\)")

    topics: dict[str, TopicConfig] = {}
    for m in topic_pattern.finditer(text):
        topic_id, title, description, n, easy, med, hard = m.groups()
        topics[topic_id] = TopicConfig(
            topic_id=topic_id,
            title=title,
            description=description,
            num_questions=int(n),
            easy_pct=int(easy),
            medium_pct=int(med),
            hard_pct=int(hard),
        )

    subtopics: list[SubtopicConfig] = []
    for m in subtopic_pattern.finditer(text):
        topic_id, name, sort_order, weight = m.groups()
        if topic_id in topics:
            subtopics.append(
                SubtopicConfig(
                    topic_id=topic_id,
                    name=name,
                    sort_order=int(sort_order),
                    weight=float(weight),
                )
            )

    if not topics:
        raise RuntimeError(f"No topic rows parsed from {schema_path}")
    if not subtopics:
        raise RuntimeError(f"No subtopic rows parsed from {schema_path}")

    return topics, subtopics


def proportional_counts(total: int, weights: list[float]) -> list[int]:
    if total <= 0:
        return [0 for _ in weights]
    if not weights:
        return []

    s = sum(weights)
    if s <= 0:
        weights = [1.0 for _ in weights]
        s = float(len(weights))

    raw = [(w / s) * total for w in weights]
    base = [int(x) for x in raw]
    remainder = total - sum(base)

    fractions = sorted(enumerate(raw), key=lambda item: item[1] - int(item[1]), reverse=True)
    for i in range(remainder):
        base[fractions[i % len(fractions)][0]] += 1

    return base


def build_distribution(topic: TopicConfig, topic_subtopics: list[SubtopicConfig], target_questions: int | None) -> dict[str, Any]:
    num_questions = target_questions or topic.num_questions

    diff_counts = proportional_counts(num_questions, [topic.easy_pct, topic.medium_pct, topic.hard_pct])
    difficulties = (
        ["easy"] * diff_counts[0]
        + ["medium"] * diff_counts[1]
        + ["hard"] * diff_counts[2]
    )

    sorted_subtopics = sorted(topic_subtopics, key=lambda s: s.sort_order)
    weights = [s.weight for s in sorted_subtopics]
    sub_counts = proportional_counts(num_questions, weights)

    subtopic_names: list[str] = []
    for st, cnt in zip(sorted_subtopics, sub_counts):
        subtopic_names.extend([st.name] * cnt)

    if len(subtopic_names) != num_questions:
        subtopic_names = (subtopic_names + [sorted_subtopics[0].name] * num_questions)[:num_questions]

    random.shuffle(difficulties)
    random.shuffle(subtopic_names)

    return {
        "num_questions": num_questions,
        "difficulties": difficulties,
        "subtopic_names": subtopic_names,
        "subtopic_weights": [
            {
                "name": st.name,
                "weight": round(st.weight / sum(weights), 6) if sum(weights) > 0 else 0,
            }
            for st in sorted_subtopics
        ],
    }


def render_prompt_payload(topic: TopicConfig, subtopic_weights: list[dict[str, Any]], num_questions: int) -> dict[str, Any]:
    return {
        "instructions": "Generate interview-style questions for the given topic. Automatically distribute questions among the subtopics based on their importance. Include a mix of difficulty levels (easy, medium, hard) suitable for interview preparation. Questions should be realistic, scenario-based where applicable, and focused on practical understanding. Each question must have 4 options and one correct answer. Provide explanation for each answer when possible.",
        "topic": topic.title,
        "subtopics": subtopic_weights,
        "num_questions": num_questions,
        "difficulty_mix": {
            "easy": topic.easy_pct,
            "medium": topic.medium_pct,
            "hard": topic.hard_pct,
        },
        "question_structure": {
            "question": "string - the MCQ question",
            "type": "MCQ",
            "difficulty": "easy | medium | hard",
            "subtopic": "string - name of the subtopic",
            "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
            "answer": "Correct Option Text",
            "explanation": "Brief explanation for the correct answer",
        },
        "requirements": [
            "Distribute questions across subtopics proportionally to their weight",
            "Include conceptual, scenario-based, and problem-solving MCQs",
            "All questions should be interview-level, not too trivial",
            "Options should be plausible, only one correct answer",
            "Vary wording and examples between questions",
            "Output JSON must be an array of question objects as per question_structure",
        ],
    }


def template_question(topic_title: str, subtopic: str, difficulty: str, i: int) -> dict[str, Any]:
    scenario_templates = [
        "Your team is building a feature under tight deadline. In the context of {subtopic}, which approach is most reliable?",
        "During an interview, you are asked to reason about {subtopic}. Which answer demonstrates practical understanding?",
        "A production issue appears related to {subtopic}. What should be your best first action?",
        "When optimizing for maintainability in {subtopic}, which decision is strongest?",
    ]
    conceptual_templates = [
        "Which statement best describes a core principle of {subtopic}?",
        "For {subtopic}, which trade-off is generally most accurate in real systems?",
        "Which option is the most interview-ready explanation of {subtopic}?",
    ]

    stems = scenario_templates if i % 2 == 0 else conceptual_templates
    stem = random.choice(stems).format(subtopic=subtopic)

    if difficulty == "easy":
        correct = "Clarify requirements, apply fundamentals, and verify with a simple measurable check."
        d1 = "Skip validation to move faster and rely only on intuition."
        d2 = "Use the most complex solution first to look advanced."
        d3 = "Ignore trade-offs because interviewers only care about buzzwords."
    elif difficulty == "medium":
        correct = "Compare alternatives with constraints, justify trade-offs, and choose the lowest-risk path."
        d1 = "Pick whichever option has the latest framework regardless of constraints."
        d2 = "Prioritize implementation speed only and postpone correctness concerns."
        d3 = "Assume edge cases are irrelevant if the main flow works once."
    else:
        correct = "Model failure modes, evaluate scalability and correctness implications, then propose mitigation steps."
        d1 = "Focus only on average-case behavior and ignore worst-case impact."
        d2 = "Choose a rigid design with no observability because metrics can be added later."
        d3 = "Optimize micro-performance before validating architecture-level bottlenecks."

    options = [correct, d1, d2, d3]
    random.shuffle(options)

    return {
        "question": f"[{topic_title}] {stem}",
        "type": "MCQ",
        "difficulty": difficulty,
        "subtopic": subtopic,
        "options": options,
        "answer": correct,
        "explanation": "The correct choice demonstrates practical reasoning: requirements/context first, trade-offs second, and validation/mitigation before finalizing decisions.",
    }


def generate_template_set(topic: TopicConfig, distribution: dict[str, Any]) -> list[dict[str, Any]]:
    n = distribution["num_questions"]
    subtopics = distribution["subtopic_names"]
    difficulties = distribution["difficulties"]

    questions = []
    for i in range(n):
        questions.append(template_question(topic.title, subtopics[i], difficulties[i], i))
    return questions


def extract_json_array(content: str) -> list[dict[str, Any]]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()

    start = stripped.find("[")
    end = stripped.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model output does not contain a JSON array")

    payload = stripped[start : end + 1]
    parsed = json.loads(payload)
    if not isinstance(parsed, list):
        raise ValueError("Parsed payload is not an array")
    return parsed


def generate_with_groq(
    topic: TopicConfig,
    distribution: dict[str, Any],
    model: str,
    api_key: str,
    batch_size: int,
    delay_s: float,
) -> list[dict[str, Any]]:
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    num = distribution["num_questions"]
    sub_weights = distribution["subtopic_weights"]
    diffs = distribution["difficulties"]

    results: list[dict[str, Any]] = []
    for start in range(0, num, batch_size):
        end = min(num, start + batch_size)
        batch_n = end - start

        batch_diff = diffs[start:end]
        easy = sum(1 for d in batch_diff if d == "easy")
        medium = sum(1 for d in batch_diff if d == "medium")
        hard = sum(1 for d in batch_diff if d == "hard")

        prompt_obj = render_prompt_payload(topic, sub_weights, batch_n)
        prompt_obj["difficulty_mix"] = {
            "easy": int(round((easy / batch_n) * 100)),
            "medium": int(round((medium / batch_n) * 100)),
            "hard": int(round((hard / batch_n) * 100)),
        }

        system = "You are an expert technical interviewer and assessment designer. Respond only with valid JSON array."
        user = (
            "Follow this JSON instruction object and output ONLY the final array of question objects. "
            "No prose, no markdown.\n\n"
            + json.dumps(prompt_obj, ensure_ascii=False)
        )

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.5,
            "max_tokens": 8192,
        }

        resp = requests.post(endpoint, headers=headers, json=body, timeout=180)
        if resp.status_code != 200:
            raise RuntimeError(f"Groq batch {start}-{end} failed: {resp.status_code} {resp.text[:300]}")

        payload = resp.json()
        content = payload["choices"][0]["message"]["content"]
        batch_questions = extract_json_array(content)

        if len(batch_questions) != batch_n:
            raise RuntimeError(
                f"Groq batch {start}-{end} length mismatch: expected {batch_n}, got {len(batch_questions)}"
            )

        results.extend(batch_questions)
        print(f"Generated {end}/{num} for topic {topic.topic_id}")
        if delay_s > 0 and end < num:
            time.sleep(delay_s)

    return results


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate bulk MCQ datasets from schema topics/subtopics.")
    parser.add_argument("--schema", default="docs/supabase_schema.sql", help="Path to SQL schema file")
    parser.add_argument("--output-dir", default="data/mcq_generated", help="Output directory")
    parser.add_argument("--topic-id", default=None, help="Generate for one topic id only")
    parser.add_argument("--num-questions", type=int, default=None, help="Override question count per topic")
    parser.add_argument("--provider", choices=["auto", "groq", "template"], default="auto")
    parser.add_argument("--model", default=os.getenv("QACE_GROQ_MODEL", "llama-3.3-70b-versatile"))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--delay", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--write-prompts", action="store_true", help="Write prompt payloads per topic")

    args = parser.parse_args()
    random.seed(args.seed)

    schema_path = Path(args.schema)
    output_dir = Path(args.output_dir)

    topics, subtopics = parse_schema(schema_path)

    topic_ids = [args.topic_id] if args.topic_id else sorted(topics.keys())
    for t in topic_ids:
        if t not in topics:
            raise RuntimeError(f"Unknown topic_id: {t}")

    api_key = os.getenv("GROQ_API_KEY", "")
    provider = args.provider
    if provider == "auto":
        provider = "groq" if api_key else "template"

    print(f"Provider: {provider}")
    print(f"Topics: {', '.join(topic_ids)}")

    manifest: list[dict[str, Any]] = []

    for topic_id in topic_ids:
        topic = topics[topic_id]
        topic_subtopics = [s for s in subtopics if s.topic_id == topic_id]
        distribution = build_distribution(topic, topic_subtopics, args.num_questions)

        if args.write_prompts:
            prompt_payload = render_prompt_payload(topic, distribution["subtopic_weights"], distribution["num_questions"])
            write_json(output_dir / "prompts" / f"{topic_id}.json", prompt_payload)

        if provider == "groq":
            if not api_key:
                raise RuntimeError("GROQ_API_KEY is required for --provider groq")
            questions = generate_with_groq(
                topic=topic,
                distribution=distribution,
                model=args.model,
                api_key=api_key,
                batch_size=args.batch_size,
                delay_s=args.delay,
            )
        else:
            questions = generate_template_set(topic, distribution)

        out = {
            "topic_id": topic.topic_id,
            "topic": topic.title,
            "num_questions": len(questions),
            "difficulty_mix": {
                "easy": topic.easy_pct,
                "medium": topic.medium_pct,
                "hard": topic.hard_pct,
            },
            "questions": questions,
        }

        out_path = output_dir / f"{topic_id}.json"
        write_json(out_path, out)
        print(f"Wrote {len(questions)} questions: {out_path}")

        manifest.append(
            {
                "topic_id": topic.topic_id,
                "topic": topic.title,
                "num_questions": len(questions),
                "file": str(out_path).replace("\\", "/"),
            }
        )

    write_json(output_dir / "manifest.json", manifest)
    print(f"Done. Manifest: {output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
