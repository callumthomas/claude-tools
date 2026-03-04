#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path

DELEGATION_TEMPLATES = {
    "explorer": {"tools": {"read", "grep", "glob"}, "model": "haiku"},
    "test-runner": {"tools": {"bash", "read", "grep"}, "model": "haiku"},
    "data-fetcher": {"tools": {"bash", "read"}, "model": "haiku"},
    "doc-researcher": {"tools": {"read", "grep", "glob", "webfetch", "websearch"}, "model": "haiku"},
    "writer": {"tools": {"bash", "read", "grep", "glob", "write"}, "model": "haiku"},
}

MAX_TURNS_RANGES = {
    "explorer": (3, 10),
    "test-runner": (5, 10),
    "data-fetcher": (5, 10),
    "doc-researcher": (10, 20),
    "writer": (10, 15),
}

STRUCTURED_RESPONSE_PATTERNS = [
    r"return\s+(only|just)",
    r"structured\s+(summary|response|output|return|format)",
    r"(response|output|return)\s+format",
    r"keep\s+(response|output|total)\s+under\s+\d+\s+tokens",
    r"CRITICAL:\s*(Do\s+NOT|Never)\s+(include|return)",
    r"```json",
    r"##\s+(Output|Response|Return)\s+Format",
]

ITERATIVE_PATTERNS = [
    r"retry\s+until",
    r"keep\s+(trying|working|going)\s+until",
    r"loop\s+until",
    r"repeat\s+until",
    r"iterate\s+until",
    r"while\s+.*\b(fail|error|not)\b",
]

TRIVIAL_DELEGATION_PATTERNS = [
    (r"(subagent|sub-?agent|delegate)\s+.*\b(read\s+one\s+file|single\s+file|one\s+file)\b", "single-file read delegation"),
    (r"(subagent|sub-?agent|delegate)\s+.*\b(simple\s+check|quick\s+check|single\s+check)\b", "trivial check delegation"),
    (r"(spawn|create|use)\s+(a\s+)?(subagent|sub-?agent)\s+to\s+(read|check|verify)\s+\w+$", "tiny task delegation"),
]

SCALE_EXCLUSIONS = ["multiple", "several", "all", "batch", "sequential", "many"]


def parse_frontmatter_and_body(content):
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return parts[1].strip(), parts[2].strip()
    return "", content.strip()


def parse_frontmatter_fields(frontmatter_text):
    fields = {}
    for key in ("name", "description", "model", "tools", "maxTurns", "max_turns"):
        pattern = rf"^{key}:\s*(.+?)(?:\n\S|\Z)"
        match = re.search(pattern, frontmatter_text, re.MULTILINE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value.startswith(">"):
                value = value[1:].strip()
            value = re.sub(r"\s+", " ", value)
            fields[key] = value
    return fields


def parse_tools(tools_str):
    if not tools_str:
        return []
    return [t.strip() for t in re.split(r"[,\s]+", tools_str) if t.strip()]


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


def closest_template(agent_tools):
    agent_set = {t.lower() for t in agent_tools}
    best_match = None
    best_overlap = 0.0
    for name, template in DELEGATION_TEMPLATES.items():
        expected = template["tools"]
        union = agent_set | expected
        if not union:
            continue
        overlap = len(agent_set & expected) / len(union)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = name
    return best_match, best_overlap


def has_iterative_pattern(text):
    for pattern in ITERATIVE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def has_structured_response(text):
    for pattern in STRUCTURED_RESPONSE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def classify_task_type(description, tools):
    description_lower = (description or "").lower()
    tool_set = {t.lower() for t in tools}

    if any(kw in description_lower for kw in ["explore", "search", "find", "discover", "gather", "read"]):
        return "explorer"
    if any(kw in description_lower for kw in ["test", "pytest", "jest", "run test"]):
        return "test-runner"
    if any(kw in description_lower for kw in ["fetch", "extract", "mcp", "api", "data"]):
        return "data-fetcher"
    if any(kw in description_lower for kw in ["research", "documentation", "web"]):
        return "doc-researcher"
    if any(kw in description_lower for kw in ["write", "generate", "create", "process", "transform"]):
        return "writer"

    if tool_set <= {"read", "grep", "glob"}:
        return "explorer"
    if "webfetch" in tool_set or "websearch" in tool_set:
        return "doc-researcher"
    if "write" in tool_set:
        return "writer"

    return None


def analyze_agent(file_path):
    content = file_path.read_text(encoding="utf-8", errors="replace")
    frontmatter_text, body = parse_frontmatter_and_body(content)
    fields = parse_frontmatter_fields(frontmatter_text)

    name = fields.get("name", file_path.stem)
    tools = parse_tools(fields.get("tools", ""))
    description = fields.get("description", "")

    max_turns_str = fields.get("maxTurns") or fields.get("max_turns")
    has_mt = max_turns_str is not None
    mt_value = None
    if has_mt:
        try:
            mt_value = int(max_turns_str)
        except (ValueError, TypeError):
            has_mt = False

    has_sr = has_structured_response(body)
    is_iterative = has_iterative_pattern(body)

    tmpl_name, tmpl_score = closest_template(tools)
    tool_set = {t.lower() for t in tools}
    extra_tools = []
    if tmpl_name:
        expected = DELEGATION_TEMPLATES[tmpl_name]["tools"]
        extra_tools = sorted(t for t in tools if t.lower() not in expected)

    findings = []

    if not has_mt:
        severity = "HIGH" if is_iterative else "MEDIUM"
        findings.append({
            "category": "missing_max_turns",
            "severity": severity,
            "detail": f"Agent '{name}' has no maxTurns field" + (" (iterative pattern detected)" if is_iterative else ""),
            "fix": "Add maxTurns to agent frontmatter to prevent runaway loops",
        })

    if not has_sr:
        findings.append({
            "category": "missing_structured_response",
            "severity": "MEDIUM",
            "detail": f"Agent '{name}' has no structured response format guidance",
            "fix": "Add response format instructions with token limit (e.g., 'Keep response under 1,000 tokens')",
        })

    read_only_keywords = {"read", "grep", "glob"}
    is_read_only_by_desc = any(
        kw in (description or "").lower()
        for kw in ["explore", "search", "find", "read", "gather", "scan"]
    )
    has_write_tools = bool(tool_set & {"bash", "write", "edit", "notebookedit"})
    if is_read_only_by_desc and has_write_tools:
        findings.append({
            "category": "overly_broad_tools",
            "severity": "MEDIUM",
            "detail": f"Agent '{name}' appears read-only by description but has write tools: {', '.join(t for t in tools if t.lower() in {'bash', 'write', 'edit', 'notebookedit'})}",
            "fix": f"Scope tools to match task; consider explorer template (Read, Grep, Glob)",
        })
    elif len(tools) > 5 and tmpl_score < 0.4:
        findings.append({
            "category": "overly_broad_tools",
            "severity": "MEDIUM",
            "detail": f"Agent '{name}' has {len(tools)} tools and doesn't match any delegation template",
            "fix": "Reduce tool set to match a known delegation template",
        })

    if has_mt and mt_value is not None:
        task_type = classify_task_type(description, tools)
        if task_type and task_type in MAX_TURNS_RANGES:
            low, high = MAX_TURNS_RANGES[task_type]
            if mt_value < low or mt_value > high:
                findings.append({
                    "category": "max_turns_mismatch",
                    "severity": "LOW",
                    "detail": f"Agent '{name}' ({task_type}) has maxTurns={mt_value}, recommended range is {low}-{high}",
                    "fix": f"Adjust maxTurns to {low}-{high} for {task_type} tasks",
                })

    return {
        "name": name,
        "file": file_path.name,
        "tools": tools,
        "has_max_turns": has_mt,
        "max_turns_value": mt_value,
        "has_structured_response": has_sr,
        "closest_template": tmpl_name,
        "template_match_score": round(tmpl_score, 2),
        "extra_tools": extra_tools,
        "findings": findings,
    }


def scan_skill_md_for_delegation_issues(body):
    findings = []

    for regex, label in TRIVIAL_DELEGATION_PATTERNS:
        for m in re.finditer(regex, body, re.IGNORECASE | re.MULTILINE):
            if has_nearby_context(body, m.start(), SCALE_EXCLUSIONS):
                continue
            location = find_location(body, m.group())
            findings.append({
                "category": "trivial_delegation",
                "severity": "LOW",
                "location": location,
                "match": m.group().strip(),
                "detail": f"Detected {label} — spawn overhead (~500-1,000 tokens) may exceed savings",
                "fix": "Perform this operation directly in the main thread",
            })
            break

    return findings


def find_agent_files(skill_dir, agents_dir=None):
    agent_files = []

    for md_file in skill_dir.glob("*.md"):
        if md_file.name.lower() in ("skill.md", "readme.md"):
            continue
        agent_files.append(md_file)

    agents_subdir = skill_dir / "agents"
    if agents_subdir.is_dir():
        for md_file in agents_subdir.glob("*.md"):
            agent_files.append(md_file)

    if agents_dir:
        agents_path = Path(agents_dir)
        if agents_path.is_dir():
            for md_file in agents_path.glob("*.md"):
                agent_files.append(md_file)

    return agent_files


def main():
    parser = argparse.ArgumentParser(
        description="Audit agent files against delegation patterns."
    )
    parser.add_argument(
        "skill_dir",
        help="Path to the skill directory",
    )
    parser.add_argument(
        "--agents-dir",
        help="Path to additional agents directory",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)

    agents_analyzed = []
    agent_files = find_agent_files(skill_dir, args.agents_dir)
    for af in agent_files:
        agents_analyzed.append(analyze_agent(af))

    skill_md_findings = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.is_file():
        content = skill_md.read_text(encoding="utf-8", errors="replace")
        _fm, body = parse_frontmatter_and_body(content)
        skill_md_findings = scan_skill_md_for_delegation_issues(body)

    all_findings = list(skill_md_findings)
    for agent in agents_analyzed:
        all_findings.extend(agent.get("findings", []))

    high = sum(1 for f in all_findings if f["severity"] == "HIGH")
    medium = sum(1 for f in all_findings if f["severity"] == "MEDIUM")
    low = sum(1 for f in all_findings if f["severity"] == "LOW")
    score = max(0, 10 - (high * 3) - (medium * 1))

    without_mt = sum(1 for a in agents_analyzed if not a["has_max_turns"])
    without_sr = sum(1 for a in agents_analyzed if not a["has_structured_response"])

    result = {
        "agents_analyzed": agents_analyzed,
        "skill_md_findings": skill_md_findings,
        "summary": {
            "total_findings": len(all_findings),
            "high": high,
            "medium": medium,
            "low": low,
            "agents_without_max_turns": without_mt,
            "agents_without_structured_response": without_sr,
            "delegation_hygiene_score": score,
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
