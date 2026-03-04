#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path

READ_ONLY_TOOLS = {"read", "grep", "glob"}
RESEARCH_TOOLS = {"webfetch", "websearch"}
WRITE_TOOLS = {"write", "edit", "bash"}

PLANNING_KEYWORDS = [
    "planning", "architecture", "architectural", "security analysis",
    "complex debugging", "debugging", "strategic", "prioritisation",
    "threat model", "cross-domain", "novel reasoning", "orchestrat",
    "design decision", "tradeoff", "trade-off",
]


def parse_frontmatter(content):
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    raw = parts[1]
    fields = {}

    for key in ("name", "model", "description", "tools"):
        pattern = rf"^{key}:\s*(.+?)(?:\n\S|\Z)"
        match = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value.startswith(">"):
                value = value[1:].strip()
            value = re.sub(r"\s+", " ", value)
            fields[key] = value

    return fields


def parse_tools(tools_raw):
    if not tools_raw:
        return []

    cleaned = tools_raw.strip("[]")
    parts = [t.strip().strip("'\"") for t in re.split(r"[,\n]+", cleaned)]
    return [t for t in parts if t]


def classify_tools(tools):
    tool_names_lower = {t.lower() for t in tools}

    has_write = bool(tool_names_lower & {t.lower() for t in WRITE_TOOLS})
    has_research = bool(tool_names_lower & {t.lower() for t in RESEARCH_TOOLS})
    has_read_only = bool(tool_names_lower & {t.lower() for t in READ_ONLY_TOOLS})

    if has_write:
        return "write"
    if has_research:
        return "research"
    if has_read_only:
        return "read-only"
    if not tools:
        return "unknown"
    return "other"


def description_suggests_planning(description):
    if not description:
        return False
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in PLANNING_KEYWORDS)


def recommend_model(tool_category, description):
    if description_suggests_planning(description):
        return "sonnet"

    recommendations = {
        "read-only": "haiku",
        "research": "haiku",
        "write": "sonnet",
        "unknown": "sonnet",
        "other": "sonnet",
    }
    return recommendations.get(tool_category, "sonnet")


def estimate_savings(current_model, recommended_model):
    current = current_model.lower() if current_model else "inherit"
    recommended = recommended_model.lower()

    if current == recommended:
        return "Already optimised"

    if current in ("inherit", "opus") and recommended == "haiku":
        return "5-10x cheaper per invocation"
    if current in ("inherit", "opus") and recommended == "sonnet":
        return "~5x cheaper per invocation"
    if current == "sonnet" and recommended == "haiku":
        return "~4x cheaper per invocation"

    return "Already optimised"


def is_optimised(current_model, recommended_model):
    current = current_model.lower() if current_model else "inherit"
    recommended = recommended_model.lower()
    return current == recommended


def analyse_agent(filepath):
    content = filepath.read_text(encoding="utf-8", errors="replace")
    fields = parse_frontmatter(content)

    name = fields.get("name", filepath.stem)
    current_model = fields.get("model", "inherit")
    tools = parse_tools(fields.get("tools", ""))
    description = fields.get("description", "")

    tool_category = classify_tools(tools)
    recommended = recommend_model(tool_category, description)
    savings = estimate_savings(current_model, recommended)
    optimised = is_optimised(current_model, recommended)

    has_iterative = bool(re.search(
        r"(retry until|keep working until|keep trying until|repeat until|loop until)",
        content, re.IGNORECASE,
    ))
    has_max_turns = bool(re.search(r"max.?[Tt]urns|maxTurns|max_turns", content, re.IGNORECASE))

    result = {
        "name": name,
        "file": filepath.name,
        "current_model": current_model,
        "tools": tools,
        "tool_category": tool_category,
        "recommended_model": recommended,
        "is_optimised": optimised,
        "estimated_savings": savings,
    }

    if has_iterative and not has_max_turns:
        result["warning"] = "Iterative instructions without maxTurns guard"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Audit model routing for agent .md files in a directory."
    )
    parser.add_argument(
        "agents_dir",
        help="Path to directory containing agent .md files",
    )
    args = parser.parse_args()

    agents_dir = Path(args.agents_dir)
    if not agents_dir.is_dir():
        print(f"Error: not a directory: {args.agents_dir}", file=sys.stderr)
        sys.exit(1)

    md_files = sorted(agents_dir.glob("*.md"))
    if not md_files:
        result = {
            "agents_found": 0,
            "agents_with_explicit_model": 0,
            "agents": [],
            "summary": {
                "total_mismatches": 0,
                "potential_savings_description": "No agent files found",
            },
        }
        print(json.dumps(result, indent=2))
        return

    agents = []
    for md_file in md_files:
        agents.append(analyse_agent(md_file))

    agents_with_explicit = sum(
        1 for a in agents if a["current_model"] not in ("inherit", "")
    )
    mismatches = sum(1 for a in agents if not a["is_optimised"])

    missing_max_turns = sum(1 for a in agents if "warning" in a)

    total = len(agents)
    if mismatches > 0:
        savings_desc = f"{mismatches} of {total} subagents could run on cheaper models"
    else:
        savings_desc = "All subagents are optimally routed"

    summary = {
        "total_mismatches": mismatches,
        "potential_savings_description": savings_desc,
    }
    if missing_max_turns > 0:
        summary["missing_max_turns"] = f"{missing_max_turns} subagent(s) have iterative patterns without maxTurns"

    result = {
        "agents_found": total,
        "agents_with_explicit_model": agents_with_explicit,
        "agents": agents,
        "summary": summary,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
