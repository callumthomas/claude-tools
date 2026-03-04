#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path

GROWTH_FACTOR = 1.6

PATTERNS = {
    "sequential_file_reads": {
        "regexes": [
            r"read\s+(all|each|every)\s+file",
            r"scan\s+the\s+(codebase|directory|project|repo)",
            r"read\s+all\s+files\s+in",
            r"explore\s+the\s+directory",
            r"read\s+.*,\s*read\s+.*,\s*read\s+",
            r"(Read|read)\s+tool.*Read\s+tool.*Read\s+tool",
            r"consecutive\s+(Read|Bash)\s+calls",
            r"read\s+(multiple|several|many)\s+files",
            r"for\s+each\s+file\s+in",
            r"iterate\s+(over|through)\s+(all\s+)?files",
        ],
        "keywords": [
            "read all files",
            "scan the codebase",
            "explore the directory",
            "read each file",
            "read every file",
            "read multiple files",
        ],
        "tokens_per_occurrence": 4000,
        "frequency_per_turn": 1.0,
        "recommended_delegation": "haiku-explorer",
        "summary_tokens": 300,
    },
    "unfiltered_mcp_responses": {
        "regexes": [
            r"mcp\s+tool",
            r"mcp\s+server",
            r"mcp_",
            r"call\s+.*mcp",
        ],
        "keywords": [
            "mcp tool",
            "mcp server",
            "mcp response",
        ],
        "filter_keywords": [
            "filter", "summarise", "summarize", "extract",
            "parse", "relevant", "only return",
        ],
        "tokens_per_occurrence": 5000,
        "frequency_per_turn": 0.5,
        "recommended_delegation": "haiku-data-fetcher",
        "summary_tokens": 400,
    },
    "main_thread_test_execution": {
        "regexes": [
            r"run\s+tests?",
            r"execute\s+test\s+suite",
            r"npm\s+test",
            r"pytest",
            r"cargo\s+test",
            r"go\s+test",
            r"\bjest\b",
            r"\bvitest\b",
            r"make\s+test",
        ],
        "keywords": [
            "run tests", "run test", "execute test suite",
            "npm test", "pytest", "cargo test", "go test",
            "jest", "vitest", "make test",
        ],
        "delegation_keywords": [
            "subagent", "sub-agent", "delegate", "test runner",
            "test-runner",
        ],
        "tokens_per_occurrence": 3500,
        "frequency_per_turn": 0.3,
        "recommended_delegation": "haiku-test-runner",
        "summary_tokens": 200,
    },
    "documentation_fetching": {
        "regexes": [
            r"fetch\s+documentation",
            r"look\s+up\s+.*docs",
            r"look\s+up\s+.*api",
            r"WebFetch",
            r"WebSearch",
            r"web\s+fetch",
            r"web\s+search",
            r"search\s+the\s+web",
            r"fetch\s+.*from\s+.*url",
        ],
        "keywords": [
            "fetch documentation", "look up api docs",
            "WebFetch", "WebSearch", "web fetch", "web search",
            "search the web",
        ],
        "delegation_keywords": [
            "subagent", "sub-agent", "delegate", "doc researcher",
            "doc-researcher",
        ],
        "tokens_per_occurrence": 6000,
        "frequency_per_turn": 0.3,
        "recommended_delegation": "haiku-doc-researcher",
        "summary_tokens": 500,
    },
    "log_analysis": {
        "regexes": [
            r"parse\s+logs?",
            r"read\s+log\s+files?",
            r"analy[sz]e\s+(error\s+)?logs?",
            r"check\s+.*log\s+output",
            r"inspect\s+.*logs?",
        ],
        "keywords": [
            "parse logs", "read log files", "analyse error logs",
            "analyze error logs", "check log output",
        ],
        "tokens_per_occurrence": 2000,
        "frequency_per_turn": 0.3,
        "recommended_delegation": "haiku-explorer",
        "summary_tokens": 300,
    },
    "sequential_independent_tool_calls": {
        "regexes": [
            r"then\s+(read|grep|glob|search|fetch|check)\b",
            r"first\s+(read|grep|glob|search|fetch).*then\s+(read|grep|glob|search|fetch)",
            r"after\s+that,?\s+(read|grep|glob|search|fetch)",
            r"next,?\s+(read|grep|glob|search|fetch)",
        ],
        "keywords": [
            "then read", "then search", "then fetch",
            "then grep", "then glob",
        ],
        "delegation_keywords": [
            "parallel", "concurrently", "simultaneously",
            "in parallel",
        ],
        "tokens_per_occurrence": 1500,
        "frequency_per_turn": 0.5,
        "recommended_delegation": "parallel-tool-calls",
        "summary_tokens": 0,
    },
    "unrestricted_tool_permissions": {
        "regexes": [
            r"tools?:\s*.*Bash.*Read",
            r"tools?:\s*.*Read.*Bash",
            r"tools?:\s*.*Bash.*WebFetch",
            r"tools?:\s*.*WebFetch.*Bash",
            r"allowed.tools?.*Bash",
        ],
        "keywords": [],
        "tokens_per_occurrence": 1500,
        "frequency_per_turn": 1.0,
        "recommended_delegation": "scope-limited-subagents",
        "summary_tokens": 0,
    },
}


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

    for i, line in enumerate(lines):
        step_match = step_pattern.match(line)
        if step_match:
            current_section = line.strip().lstrip("#").strip()

        if match_lower in line.lower():
            return current_section

    return current_section


def has_nearby_filtering(body, match_pos, filter_keywords, window=300):
    start = max(0, match_pos - window)
    end = min(len(body), match_pos + window)
    context = body[start:end].lower()
    return any(kw in context for kw in filter_keywords)


def scan_for_pattern(body, pattern_name, pattern_config):
    detections = []
    body_lower = body.lower()

    matched_positions = []

    for regex in pattern_config["regexes"]:
        for m in re.finditer(regex, body, re.IGNORECASE):
            matched_positions.append((m.start(), m.group()))

    for kw in pattern_config.get("keywords", []):
        idx = body_lower.find(kw.lower())
        if idx >= 0:
            already_covered = any(
                abs(idx - pos) < len(kw) for pos, _ in matched_positions
            )
            if not already_covered:
                matched_positions.append((idx, kw))

    if not matched_positions:
        return []

    filter_kws = pattern_config.get("filter_keywords", [])
    delegation_kws = pattern_config.get("delegation_keywords", [])

    for pos, match_text in matched_positions:
        if filter_kws and has_nearby_filtering(body, pos, filter_kws):
            continue

        if delegation_kws and has_nearby_filtering(body, pos, delegation_kws):
            continue

        location = find_location(body, match_text)
        tokens_per = pattern_config["tokens_per_occurrence"]
        summary_tokens = pattern_config["summary_tokens"]
        freq = pattern_config["frequency_per_turn"]

        cumulative = int(tokens_per * freq * 20 * GROWTH_FACTOR)

        detection = {
            "type": pattern_name,
            "location": location,
            "description": f"Detected pattern: '{match_text.strip()}'",
            "estimated_tokens_per_occurrence": tokens_per,
            "cumulative_waste_20_turns": cumulative,
            "recommended_delegation": pattern_config["recommended_delegation"],
            "estimated_summary_tokens": summary_tokens,
            "savings_per_turn": tokens_per - summary_tokens,
        }
        detections.append(detection)
        break

    return detections


def main():
    parser = argparse.ArgumentParser(
        description="Scan a SKILL.md file for context pollution patterns."
    )
    parser.add_argument(
        "skill_md",
        help="Path to the SKILL.md file to scan",
    )
    args = parser.parse_args()

    skill_path = Path(args.skill_md)
    if not skill_path.is_file():
        print(f"Error: file not found: {args.skill_md}", file=sys.stderr)
        sys.exit(1)

    content = skill_path.read_text(encoding="utf-8", errors="replace")
    _frontmatter, body = parse_frontmatter_and_body(content)

    all_detections = []
    for pattern_name, pattern_config in PATTERNS.items():
        detections = scan_for_pattern(body, pattern_name, pattern_config)
        all_detections.extend(detections)

    total_waste = sum(d["cumulative_waste_20_turns"] for d in all_detections)

    result = {
        "patterns_detected": all_detections,
        "total_patterns": len(all_detections),
        "total_estimated_waste_per_session": total_waste,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
