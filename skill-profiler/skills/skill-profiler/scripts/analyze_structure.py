#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path

from _common import (
    estimate_tokens_file,
    estimate_tokens_text,
    has_xml_brackets,
    is_kebab_case,
    parse_frontmatter,
)


def find_inline_sections(body):
    sections = []
    lines = body.splitlines()
    header_pattern = re.compile(r"^#{2,3}\s+(.*)", re.IGNORECASE)
    flagged_keywords = {"troubleshooting", "example", "error", "faq"}

    current_header = None
    current_start = 0
    current_keyword = None

    for i, line in enumerate(lines):
        match = header_pattern.match(line)
        if match:
            if current_header and current_keyword:
                line_count = i - current_start
                sections.append((current_header, current_keyword, line_count, current_start))

            header_text = match.group(1).lower()
            matched_keyword = None
            for kw in flagged_keywords:
                if kw in header_text:
                    matched_keyword = kw
                    break

            if matched_keyword:
                current_header = match.group(1)
                current_start = i
                current_keyword = matched_keyword
            else:
                current_header = None
                current_keyword = None

    if current_header and current_keyword:
        line_count = len(lines) - current_start
        sections.append((current_header, current_keyword, line_count, current_start))

    return sections


def count_directory_files(dir_path):
    if not dir_path.is_dir():
        return 0
    return sum(1 for f in dir_path.iterdir() if f.is_file())


def evaluate_description_quality(description):
    length = len(description) if description else 0
    has_use_when = bool(re.search(r"[Uu]se\s+when", description)) if description else False
    has_negative_triggers = bool(
        re.search(r"[Dd]o\s+[Nn][Oo][Tt]\s+use|[Nn]ot\s+for", description)
    ) if description else False

    trigger_phrase_pattern = re.compile(r'"[^"]{5,}"')
    action_verb_pattern = re.compile(
        r"\b(profile|analyse|analyze|audit|check|scan|optimise|optimize|review|run|create|generate|build|deploy|test|debug|fix|update|migrate)\s+\w+",
        re.IGNORECASE,
    )
    trigger_phrases = []
    if description:
        trigger_phrases.extend(trigger_phrase_pattern.findall(description))
        trigger_phrases.extend(m.group(0) for m in action_verb_pattern.finditer(description))

    domain_terms = []
    domain_keywords = [
        "SKILL.md", "agent", ".md", "config", "token", "model", "subagent",
        "context", "prompt", "skill", "routing", "cache", "frontmatter",
        "yaml", "markdown", "delegation", "haiku", "sonnet", "opus",
    ]
    if description:
        for term in domain_keywords:
            if term.lower() in description.lower():
                domain_terms.append(term)

    length_score = 2 if length > 100 else (1 if length >= 50 else 0)

    trigger_clause_score = 2 if has_use_when else 0
    if not has_use_when and description and re.search(r"[Uu]se\s+(for|to)\b", description):
        trigger_clause_score = 1

    negative_score = 2 if has_negative_triggers else 0
    if not has_negative_triggers and description and re.search(r"[Nn]ot\s+(intended|designed|meant)\s+for", description):
        negative_score = 1

    phrase_count = len(set(trigger_phrases))
    phrase_score = 2 if phrase_count >= 3 else (1 if phrase_count >= 1 else 0)

    domain_count = len(set(domain_terms))
    domain_score = 2 if domain_count >= 3 else (1 if domain_count >= 1 else 0)

    total = length_score + trigger_clause_score + negative_score + phrase_score + domain_score

    return {
        "length": length,
        "has_use_when": has_use_when,
        "has_negative_triggers": has_negative_triggers,
        "trigger_phrases_found": list(set(trigger_phrases)),
        "quality_score": total,
    }


def detect_anti_patterns(structure, description_quality, inline_sections, body="", skill_dir=None):
    patterns = []

    if structure["body_lines"] > 500:
        patterns.append({
            "pattern": "monolithic_skill_md",
            "severity": "HIGH",
            "detail": f"SKILL.md is {structure['body_lines']} lines (target: <500)",
            "fix": "Move examples and troubleshooting to references/",
        })

    if structure["body_estimated_tokens"] > 10000:
        patterns.append({
            "pattern": "high_token_body",
            "severity": "HIGH",
            "detail": f"SKILL.md body is ~{structure['body_estimated_tokens']} tokens (target: <10,000)",
            "fix": "Extract detailed content to references/ files",
        })

    if structure["references_count"] == 0 and structure["body_lines"] > 300:
        patterns.append({
            "pattern": "no_progressive_disclosure",
            "severity": "HIGH",
            "detail": f"No references/ files but body is {structure['body_lines']} lines",
            "fix": "Create references/ directory and move detailed content there",
        })

    if description_quality["length"] < 100:
        patterns.append({
            "pattern": "vague_description",
            "severity": "MEDIUM",
            "detail": f"Description is only {description_quality['length']} chars (target: >100)",
            "fix": "Add trigger phrases, use cases, and negative triggers to description",
        })

    if not description_quality["has_use_when"]:
        patterns.append({
            "pattern": "missing_trigger_clause",
            "severity": "MEDIUM",
            "detail": "Description missing 'Use when' trigger clause",
            "fix": "Add 'Use when user says ...' with specific trigger phrases",
        })

    if not description_quality["has_negative_triggers"]:
        patterns.append({
            "pattern": "missing_negative_triggers",
            "severity": "MEDIUM",
            "detail": "Description missing 'Do NOT use' exclusion clause",
            "fix": "Add 'Do NOT use for ...' to reduce false positive triggers",
        })

    for header, keyword, line_count, start_line in inline_sections:
        if keyword == "troubleshooting" and line_count > 30:
            patterns.append({
                "pattern": "inline_troubleshooting",
                "severity": "MEDIUM",
                "detail": f"Troubleshooting section '{header}' is {line_count} lines (threshold: 30)",
                "fix": "Move to references/troubleshooting.md",
            })
        if keyword in ("example", "error", "faq") and line_count > 20:
            patterns.append({
                "pattern": f"inline_{keyword}_too_long",
                "severity": "MEDIUM",
                "detail": f"Section '{header}' is {line_count} lines (threshold: 20)",
                "fix": f"Move to references/{keyword}s.md",
            })

    if structure["scripts_count"] == 0:
        patterns.append({
            "pattern": "no_scripts",
            "severity": "MEDIUM",
            "detail": "No scripts/ directory for deterministic validation",
            "fix": "Move validation and data processing logic to scripts/",
        })

    if not structure["folder_naming_valid"]:
        patterns.append({
            "pattern": "invalid_folder_name",
            "severity": "HIGH",
            "detail": "Folder name is not kebab-case",
            "fix": "Rename folder to lowercase with hyphens only",
        })

    if not structure["skill_md_exists"]:
        patterns.append({
            "pattern": "missing_skill_md",
            "severity": "HIGH",
            "detail": "SKILL.md not found (exact casing required)",
            "fix": "Create SKILL.md with proper frontmatter and body",
        })

    if not structure["no_readme"]:
        patterns.append({
            "pattern": "readme_present",
            "severity": "MEDIUM",
            "detail": "README.md found in skill folder (not allowed by standard)",
            "fix": "Remove README.md; use SKILL.md as the primary file",
        })

    if body:
        iterative_match = re.search(
            r"(retry until|keep working until|keep trying until|repeat until|loop until)",
            body, re.IGNORECASE,
        )
        has_max_turns = bool(re.search(r"max.?[Tt]urns|maxTurns|max_turns", body, re.IGNORECASE))
        if iterative_match and not has_max_turns:
            patterns.append({
                "pattern": "no_max_turns_on_iterative_subagent",
                "severity": "HIGH",
                "detail": f"Iterative pattern '{iterative_match.group()}' found without maxTurns guard",
                "fix": "Add maxTurns limit to prevent runaway subagent loops",
            })

    if body:
        enforcement_matches = re.findall(
            r"(do not delete|never delete|always confirm|must confirm before|do not remove|never remove|always ask before|do not overwrite)",
            body, re.IGNORECASE,
        )
        if enforcement_matches:
            unique = list(set(m.lower() for m in enforcement_matches))[:3]
            patterns.append({
                "pattern": "prompting_as_enforcement",
                "severity": "MEDIUM",
                "detail": f"Found prompt-based constraints: {', '.join(unique)}",
                "fix": "Consider using hooks for hard constraints instead of prompt instructions",
            })

    if body:
        vague_matches = re.findall(
            r"(handle\s+(?:it\s+)?appropriately|process\s+as\s+needed|do\s+the\s+right\s+thing|as\s+(?:you\s+)?see\s+fit|use\s+(?:your\s+)?(?:best\s+)?jud[ge]ment)",
            body, re.IGNORECASE,
        )
        if vague_matches:
            unique = list(set(m.lower() for m in vague_matches))[:3]
            patterns.append({
                "pattern": "vague_instructions",
                "severity": "LOW",
                "detail": f"Found vague instruction phrases: {', '.join(unique)}",
                "fix": "Replace with specific criteria or decision logic",
            })

    if body:
        step_count = len(re.findall(r"^#{1,4}\s+Step\s+\d+", body, re.MULTILINE | re.IGNORECASE))
        has_state_write = bool(re.search(
            r"(write|save|persist|store|update)\s+(to\s+)?(state|notes|todo|progress|checkpoint|memory|status)\s*(file|\.md|\.json|\.txt)?",
            body, re.IGNORECASE,
        ))
        has_external_memory = bool(re.search(
            r"(NOTES\.md|TODO\.md|state\.json|progress\.json|checkpoint|\.state|memory\s+file|status\s+file)",
            body, re.IGNORECASE,
        ))
        multi_session = bool(re.search(
            r"(multi.?session|across\s+sessions|between\s+sessions|resume\s+later|pick\s+up\s+where)",
            body, re.IGNORECASE,
        ))
        if (step_count > 10 or multi_session) and not has_state_write and not has_external_memory:
            detail = f"Skill has {step_count} steps" if step_count > 10 else "Multi-session skill detected"
            patterns.append({
                "pattern": "long_running_without_external_memory",
                "severity": "HIGH",
                "detail": f"{detail} without external memory/state persistence",
                "fix": "Add state file writes (e.g., NOTES.md, progress.json) to survive context compaction",
            })

    if body:
        fast_mode_match = re.search(
            r"(fast\s+mode|--fast|/fast)\s.*(ci|cd|pipeline|automated|background|cron|hook|non.?interactive|headless|batch)",
            body, re.IGNORECASE,
        )
        if not fast_mode_match:
            fast_mode_match = re.search(
                r"(ci|cd|pipeline|automated|background|cron|hook|non.?interactive|headless|batch)\s.*(fast\s+mode|--fast|/fast)",
                body, re.IGNORECASE,
            )
        if fast_mode_match:
            patterns.append({
                "pattern": "fast_mode_non_interactive",
                "severity": "HIGH",
                "detail": f"Fast mode referenced in non-interactive context: '{fast_mode_match.group().strip()}'",
                "fix": "Use standard mode for CI/CD and automated workflows; fast mode is for interactive sessions only",
            })

    if skill_dir:
        project_root = skill_dir
        for _ in range(5):
            if (project_root / ".git").exists():
                break
            if project_root.parent == project_root:
                break
            project_root = project_root.parent

        historical_dirs = []
        claude_dir = project_root / ".claude"
        if claude_dir.is_dir():
            for subdir in ("completions", "sessions", "history"):
                if (claude_dir / subdir).is_dir():
                    historical_dirs.append(f".claude/{subdir}")
        for dirname in ("sessions", "completions"):
            if (project_root / dirname).is_dir():
                historical_dirs.append(dirname)

        if historical_dirs and not (project_root / ".claudeignore").is_file():
            patterns.append({
                "pattern": "historical_dirs_without_claudeignore",
                "severity": "MEDIUM",
                "detail": f"Project has historical directories ({', '.join(historical_dirs)}) without .claudeignore",
                "fix": "Add .claudeignore to prevent auto-loading of historical context",
            })

    if skill_dir:
        agent_files = [
            f for f in skill_dir.glob("*.md")
            if f.name not in ("SKILL.md", "README.md")
        ]
        for agent_file in agent_files:
            try:
                agent_content = agent_file.read_text(encoding="utf-8", errors="replace")
                has_iterative = bool(re.search(
                    r"(retry until|keep working until|keep trying until|repeat until|loop until)",
                    agent_content, re.IGNORECASE,
                ))
                has_max_turns = bool(re.search(r"max.?[Tt]urns|maxTurns|max_turns", agent_content, re.IGNORECASE))
                if has_iterative and not has_max_turns:
                    patterns.append({
                        "pattern": "no_max_turns_on_iterative_subagent",
                        "severity": "HIGH",
                        "detail": f"Agent file {agent_file.name} has iterative instructions without maxTurns",
                        "fix": "Add maxTurns limit to prevent runaway subagent loops",
                    })
            except (OSError, UnicodeDecodeError):
                pass

    return patterns


def calculate_progressive_disclosure(structure, level3_tokens):
    score = 0
    if structure["references_count"] > 0:
        score += 3
    if structure["scripts_count"] > 0:
        score += 2
    if structure["body_lines"] < 500:
        score += 2
    if structure["body_estimated_tokens"] < 10000:
        score += 2
    if structure["frontmatter_tokens"] < 150:
        score += 1

    potential_savings = 0
    if structure["body_estimated_tokens"] > 10000:
        potential_savings = structure["body_estimated_tokens"] - 10000
    elif structure["body_lines"] > 500:
        potential_savings = int(structure["body_estimated_tokens"] * 0.4)

    return {
        "level1_tokens": structure["frontmatter_tokens"],
        "level2_tokens": structure["body_estimated_tokens"],
        "level3_tokens": level3_tokens,
        "level3_potential_savings": potential_savings,
        "compliance_score": score,
    }


def analyze_skill(skill_dir):
    skill_dir = Path(skill_dir).resolve()
    folder_name = skill_dir.name

    skill_md_path = skill_dir / "SKILL.md"
    skill_md_exists = skill_md_path.is_file()
    folder_naming_valid = is_kebab_case(folder_name)
    no_readme = not (skill_dir / "README.md").is_file()

    refs_dir = skill_dir / "references"
    scripts_dir = skill_dir / "scripts"
    references_count = count_directory_files(refs_dir)
    scripts_count = count_directory_files(scripts_dir)

    frontmatter = None
    body = ""
    raw_frontmatter = ""
    frontmatter_valid = False
    description = ""

    if skill_md_exists:
        content = skill_md_path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_frontmatter(content)
        if parsed and parsed[0] is not None:
            frontmatter, body, raw_frontmatter = parsed
            frontmatter_valid = True

            if has_xml_brackets(raw_frontmatter):
                frontmatter_valid = False

            name_field = frontmatter.get("name", "")
            if name_field and not is_kebab_case(name_field):
                frontmatter_valid = False

            description = frontmatter.get("description", "")
            if not description:
                frontmatter_valid = False
            elif len(description) > 1024:
                frontmatter_valid = False
        else:
            body = content

    body_lines = len(body.strip().splitlines()) if body.strip() else 0
    body_estimated_tokens = estimate_tokens_text(body)
    frontmatter_tokens = estimate_tokens_text(raw_frontmatter) if raw_frontmatter else 0

    level3_tokens = 0
    for d in [refs_dir, scripts_dir]:
        if d.is_dir():
            for f in d.rglob("*"):
                if f.is_file():
                    level3_tokens += estimate_tokens_file(f)

    structure = {
        "skill_md_exists": skill_md_exists,
        "folder_naming_valid": folder_naming_valid,
        "no_readme": no_readme,
        "frontmatter_valid": frontmatter_valid,
        "body_lines": body_lines,
        "body_estimated_tokens": body_estimated_tokens,
        "frontmatter_tokens": frontmatter_tokens,
        "references_count": references_count,
        "scripts_count": scripts_count,
    }

    description_quality = evaluate_description_quality(description)

    inline_sections = find_inline_sections(body) if body else []

    anti_patterns = detect_anti_patterns(structure, description_quality, inline_sections, body, skill_dir)

    progressive_disclosure = calculate_progressive_disclosure(structure, level3_tokens)

    return {
        "skill_name": folder_name,
        "structure": structure,
        "description_quality": description_quality,
        "anti_patterns": anti_patterns,
        "progressive_disclosure": progressive_disclosure,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyse the structure of a skill directory against the Agent Skills open standard."
    )
    parser.add_argument(
        "path",
        help="Path to a skill directory containing SKILL.md",
    )
    args = parser.parse_args()

    skill_dir = Path(args.path)
    if not skill_dir.is_dir():
        print(f"Error: not a directory: {args.path}", file=sys.stderr)
        sys.exit(1)

    result = analyze_skill(skill_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
