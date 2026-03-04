#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path

TIMESTAMP_PATTERNS = [
    (r"Date\.now\(\)", "Date.now()"),
    (r"new\s+Date\(\)", "new Date()"),
    (r"datetime\.now\(\)", "datetime.now()"),
    (r"datetime\.utcnow\(\)", "datetime.utcnow()"),
    (r"time\.time\(\)", "time.time()"),
    (r"toISOString\(\)", "toISOString()"),
    (r"\bcurrent.?date\b", "current date reference"),
    (r"\bcurrent.?time\b", "current time reference"),
    (r"\btoday'?s?\s+date\b", "today's date reference"),
    (r"\brequest.?id\b", "request ID"),
    (r"\bsession.?id\b", "session ID"),
    (r"\buuid\(\)", "uuid()"),
    (r"\buuid4\(\)", "uuid4()"),
    (r"\brandom\.\w+\(", "random value generation"),
    (r"Math\.random\(", "Math.random()"),
]

TOOL_MUTATION_PATTERNS = [
    (r"(add|remove|install|uninstall|enable|disable)\s+(mcp\s+)?(tools?|servers?)\s+(mid|during)", "tool set mutation mid-session"),
    (r"(connect|disconnect)\s+(to\s+)?(mcp|server)\s+(mid|during)", "MCP connection change mid-session"),
    (r"change\s+tool\s+(definitions?|set)", "tool definition change"),
    (r"swap\s+tools?", "tool swap"),
    (r"switch\s+(mcp\s+)?server", "server switch"),
    (r"restart\s+mcp", "MCP restart"),
    (r"reconfigure\s+mcp", "MCP reconfiguration"),
]

ORDERING_PATTERNS = [
    (r"(inject|insert|prepend|add)\s+.*\b(timestamp|date|time|session|request)\b.*\b(before|start|beginning|top|first)\b", "dynamic content prepended before static"),
    (r"\b(before|start|beginning|top|first)\b.*\b(inject|insert|prepend|add)\b.*\b(timestamp|date|time|session|request)\b", "dynamic content placed at start"),
    (r"dynamic\s+(content|data|values?)\s+(before|first|early|top)", "dynamic content before static"),
    (r"(prepend|inject)\s+(user|session|request)\s+(data|context|info)", "dynamic data prepended to context"),
]

MODEL_SWITCH_PATTERNS = [
    (r"switch\s+(to\s+)?(model|haiku|sonnet|opus)\s+(mid|during|within|partway)", "model switch mid-session"),
    (r"(change|swap|toggle)\s+model\s+(mid|during|within)", "model change mid-session"),
    (r"(start|begin)\s+with\s+(haiku|sonnet|opus).*then\s+(switch|change|move)\s+to\s+(haiku|sonnet|opus)", "sequential model switching"),
    (r"(escalate|downgrade|upgrade)\s+to\s+(haiku|sonnet|opus)\s+(mid|during|after)", "model escalation mid-session"),
]

BENIGN_CONTEXT_KEYWORDS = [
    "user message", "user input", "user provides", "user sends",
    "append to message", "in the request body",
]


def parse_frontmatter_and_body(content):
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return parts[1].strip(), parts[2].strip()
    return "", content.strip()


def find_location(body, match_text):
    lines = body.split("\n")
    step_pattern = re.compile(r"^#{1,4}\s+(Step\s+\d+|Phase\s+\d+|\d+\.)", re.IGNORECASE)
    current_section = "Body"
    match_lower = match_text.lower()
    for line in lines:
        step_match = step_pattern.match(line)
        if step_match:
            current_section = line.strip().lstrip("#").strip()
        if match_lower in line.lower():
            return current_section
    return current_section


def has_nearby_context(body, match_pos, keywords, window=200):
    start = max(0, match_pos - window)
    end = min(len(body), match_pos + window)
    context = body[start:end].lower()
    return any(kw in context for kw in keywords)


def estimate_tokens(text):
    return int(len(text.split()) * 1.3)


def scan_patterns(body, patterns, category, severity, fix_template):
    findings = []
    for regex, label in patterns:
        for m in re.finditer(regex, body, re.IGNORECASE):
            if has_nearby_context(body, m.start(), BENIGN_CONTEXT_KEYWORDS):
                continue
            location = find_location(body, m.group())
            findings.append({
                "category": category,
                "severity": severity,
                "location": location,
                "match": m.group().strip(),
                "detail": f"Detected {label} — will break cache prefix matching",
                "fix": fix_template,
            })
            break
    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Audit a skill for cache-busting patterns."
    )
    parser.add_argument(
        "skill_dir",
        help="Path to the skill directory",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        print(json.dumps({
            "findings": [],
            "summary": {
                "total_findings": 0, "high": 0, "medium": 0, "low": 0,
                "cache_hygiene_score": 10,
            },
            "cacheable_size_check": {
                "skill_md_tokens": 0,
                "meets_haiku_sonnet_minimum": False,
                "meets_opus_minimum": False,
            },
        }, indent=2))
        return

    content = skill_md.read_text(encoding="utf-8", errors="replace")
    _frontmatter, body = parse_frontmatter_and_body(content)

    findings = []

    findings.extend(scan_patterns(
        body, TIMESTAMP_PATTERNS, "timestamp_in_prompt", "HIGH",
        "Move dynamic values to user message or append after static context",
    ))

    findings.extend(scan_patterns(
        body, TOOL_MUTATION_PATTERNS, "tool_mutation_mid_session", "HIGH",
        "Use a fixed tool set per session; avoid mid-session MCP changes",
    ))

    findings.extend(scan_patterns(
        body, ORDERING_PATTERNS, "dynamic_content_ordering", "MEDIUM",
        "Place static content first, dynamic content last in prompt structure",
    ))

    findings.extend(scan_patterns(
        body, MODEL_SWITCH_PATTERNS, "model_switch_mid_session", "MEDIUM",
        "Use consistent model per session; delegate to subagents for different tiers",
    ))

    token_count = estimate_tokens(body)
    meets_haiku_sonnet = token_count >= 1024
    meets_opus = token_count >= 2048

    if not meets_haiku_sonnet:
        findings.append({
            "category": "below_cache_minimum",
            "severity": "LOW",
            "location": "Body",
            "match": f"{token_count} tokens",
            "detail": f"SKILL.md body (~{token_count} tokens) is below the 1,024-token caching minimum for Haiku/Sonnet",
            "fix": "Informational only — small skills benefit less from caching",
        })
    elif not meets_opus:
        findings.append({
            "category": "below_cache_minimum",
            "severity": "LOW",
            "location": "Body",
            "match": f"{token_count} tokens",
            "detail": f"SKILL.md body (~{token_count} tokens) is below the 2,048-token Opus caching minimum",
            "fix": "Informational only — Opus caching requires larger content blocks",
        })

    high = sum(1 for f in findings if f["severity"] == "HIGH")
    medium = sum(1 for f in findings if f["severity"] == "MEDIUM")
    low = sum(1 for f in findings if f["severity"] == "LOW")
    score = max(0, 10 - (high * 3) - (medium * 1))

    result = {
        "findings": findings,
        "summary": {
            "total_findings": len(findings),
            "high": high,
            "medium": medium,
            "low": low,
            "cache_hygiene_score": score,
        },
        "cacheable_size_check": {
            "skill_md_tokens": token_count,
            "meets_haiku_sonnet_minimum": meets_haiku_sonnet,
            "meets_opus_minimum": meets_opus,
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
