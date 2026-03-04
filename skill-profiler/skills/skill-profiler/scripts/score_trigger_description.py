#!/usr/bin/env python3

import argparse
import json
import re
import sys


STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "to", "for", "of", "in", "on", "with", "this", "that",
    "it", "its", "as", "at", "by", "from", "but", "not", "no", "if",
    "do", "does", "did", "has", "have", "had", "will", "would", "shall",
    "should", "may", "might", "can", "could", "so", "than", "too", "very",
    "just", "about", "also", "then", "them", "they", "their", "there",
    "these", "those", "we", "our", "you", "your", "he", "she", "his",
    "her", "who", "which", "what", "when", "where", "how", "all", "each",
    "any", "both", "few", "more", "most", "other", "some", "such", "only",
}

DOMAIN_TERMS = [
    "skill.md", "agent", ".md", "config", "token", "model", "subagent",
    "context", "prompt", "skill", "routing", "cache", "frontmatter",
    "yaml", "markdown", "delegation", "haiku", "sonnet", "opus",
    "api", "workflow", "pipeline", "deploy", "docker", "kubernetes",
    "terraform", "database", "schema", "migration", "test", "lint",
    "format", "build", "ci", "cd", "git", "repo", "branch", "pr",
    "review", "debug", "log", "monitor", "metric", "alert",
]


def tokenise(text):
    words = re.findall(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def score_length(description):
    length = len(description)
    if length > 100:
        return 2
    if length >= 50:
        return 1
    return 0


def score_trigger_clause(description):
    if re.search(r"[Uu]se\s+when", description):
        return 2
    if re.search(r"[Uu]se\s+(for|to)\b|[Tt]rigger|[Aa]ctivate\s+when|[Ii]nvoke\s+when", description):
        return 1
    return 0


def score_negative_triggers(description):
    if re.search(r"[Dd]o\s+[Nn][Oo][Tt]\s+use|[Dd]o\s+not\s+use", description):
        return 2
    if re.search(r"[Nn]ot\s+for|[Nn]ot\s+intended|[Ee]xclude|[Aa]void\s+using|[Nn]ot\s+designed\s+for|[Nn]ot\s+meant\s+for", description):
        return 1
    return 0


def score_trigger_phrases(description):
    quoted = re.findall(r'"[^"]{3,}"', description)

    action_verbs = re.findall(
        r"\b(profile|analyse|analyze|audit|check|scan|optimise|optimize|review|run|create|generate|build|deploy|test|debug|fix|update|migrate|help|plan|write|read|search|find|list|show|explain|compare|merge|delete|remove|add|install|configure|setup|monitor|track|report|format|lint|refactor|convert|transform|export|import|fetch|download|upload|publish|release|tag|version)\s+\w+",
        description,
        re.IGNORECASE,
    )

    total = len(set(quoted)) + len(set(action_verbs))
    if total >= 3:
        return 2
    if total >= 1:
        return 1
    return 0


def score_domain_terms(description):
    desc_lower = description.lower()
    found = []
    for term in DOMAIN_TERMS:
        if term.lower() in desc_lower:
            found.append(term)
    unique = len(set(found))
    if unique >= 3:
        return 2
    if unique >= 1:
        return 1
    return 0


def generate_suggestions(scores, description):
    suggestions = []

    if scores["length"] < 2:
        suggestions.append("Expand description to over 100 characters with more detail about what the skill does")

    if scores["trigger_clause"] < 2:
        suggestions.append("Add explicit 'Use when user says ...' clause with specific trigger phrases")

    if scores["negative_triggers"] < 2:
        suggestions.append("Add 'Do NOT use for ...' clause to prevent false positive triggers")

    if scores["trigger_phrases"] < 2:
        suggestions.append("Add more specific trigger phrases in quotes (e.g., \"profile this skill\", \"audit tokens\")")

    if scores["domain_terms"] < 2:
        suggestions.append("Mention more domain-specific terms (file types, tools, concepts) relevant to the skill")

    return suggestions


def detect_collisions(main_description, other_descriptions):
    collisions = []
    main_keywords = tokenise(main_description)

    if not main_keywords:
        return collisions

    for i, other in enumerate(other_descriptions):
        other_keywords = tokenise(other)
        if not other_keywords:
            continue

        shared = main_keywords & other_keywords
        union = main_keywords | other_keywords
        overlap_pct = len(shared) / len(union) * 100 if union else 0

        if overlap_pct > 60:
            collisions.append({
                "other_index": i,
                "other_description": other[:120] + ("..." if len(other) > 120 else ""),
                "overlap_percentage": round(overlap_pct, 1),
                "shared_keywords": sorted(shared),
            })

    return collisions


def score_description(description, other_descriptions=None):
    scores = {
        "length": score_length(description),
        "trigger_clause": score_trigger_clause(description),
        "negative_triggers": score_negative_triggers(description),
        "trigger_phrases": score_trigger_phrases(description),
        "domain_terms": score_domain_terms(description),
    }

    total = sum(scores.values())
    suggestions = generate_suggestions(scores, description)
    collisions = detect_collisions(description, other_descriptions) if other_descriptions else []

    return {
        "description": description,
        "length": len(description),
        "scores": scores,
        "total_score": total,
        "suggestions": suggestions,
        "collisions": collisions,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Score a skill trigger description for quality and detect collisions with other descriptions."
    )
    parser.add_argument(
        "--description",
        required=True,
        help="The skill description text to score",
    )
    parser.add_argument(
        "--others",
        nargs="*",
        default=[],
        help="Other skill descriptions to check for collision (each as a separate argument)",
    )
    args = parser.parse_args()

    result = score_description(args.description, args.others if args.others else None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
