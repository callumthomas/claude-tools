#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_PATH = SCRIPT_DIR / ".." / "assets" / "report-template.md"


def parse_frontmatter(content):
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    raw = parts[1]
    fields = {}
    for key in ("name", "description"):
        pattern = rf"^{key}:\s*(.+?)(?:\n\S|\Z)"
        match = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value.startswith(">"):
                value = value[1:].strip()
            value = re.sub(r"\s+", " ", value)
            fields[key] = value
    return fields


def run_script(script_name, args_list):
    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        return None, f"Script not found: {script_name}"

    cmd = [sys.executable, str(script_path)] + args_list
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            return None, proc.stderr.strip() or f"{script_name} exited with code {proc.returncode}"
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON from {script_name}: {e}"
    except subprocess.TimeoutExpired:
        return None, f"{script_name} timed out"
    except Exception as e:
        return None, f"Error running {script_name}: {e}"


def status_indicator(value, target_fn):
    result = target_fn(value)
    if result == "pass":
        return "PASS"
    if result == "warn":
        return "WARN"
    return "FAIL"


def body_lines_status(val):
    if val <= 500:
        return "pass"
    if val <= 600:
        return "warn"
    return "fail"


def body_tokens_status(val):
    if val <= 10000:
        return "pass"
    if val <= 12000:
        return "warn"
    return "fail"


def frontmatter_tokens_status(val):
    if val <= 150:
        return "pass"
    if val <= 180:
        return "warn"
    return "fail"


def references_status(count, body_lines):
    if body_lines <= 300:
        return "pass"
    if count > 0:
        return "pass"
    return "fail"


def scripts_status(count):
    if count > 0:
        return "pass"
    return "warn"


def description_score_status(score):
    if score >= 7:
        return "pass"
    if score >= 5:
        return "warn"
    return "fail"


def calculate_overall_score(structure_data, description_data, routing_data, pollution_data, cache_data, delegation_data):
    structural_score = 0
    if structure_data:
        pd = structure_data.get("progressive_disclosure", {})
        compliance = pd.get("compliance_score", 0)
        structural_score = int(compliance * 2.5)

    desc_score = 0
    if description_data:
        total = description_data.get("total_score", 0)
        desc_score = int(total * 1.5)

    routing_score = 20
    if routing_data:
        agents = routing_data.get("agents", [])
        if agents:
            optimised = sum(1 for a in agents if a.get("is_optimised"))
            routing_score = int((optimised / len(agents)) * 20)
        else:
            routing_score = 20

    pollution_score = 20
    if pollution_data:
        pattern_count = pollution_data.get("total_patterns", 0)
        if pattern_count >= 5:
            pollution_score = 0
        else:
            pollution_score = int(20 - (pattern_count * 4))

    cache_score = 10
    if cache_data:
        high = cache_data.get("summary", {}).get("high", 0)
        medium = cache_data.get("summary", {}).get("medium", 0)
        cache_score = max(0, 10 - (high * 3) - (medium * 1))

    delegation_score = 10
    if delegation_data:
        high = delegation_data.get("summary", {}).get("high", 0)
        medium = delegation_data.get("summary", {}).get("medium", 0)
        delegation_score = max(0, 10 - (high * 3) - (medium * 1))

    return min(100, max(0, structural_score + desc_score + routing_score + pollution_score + cache_score + delegation_score))


def build_model_routing_section(routing_data):
    if not routing_data:
        return "Not included in this mode. Run with `--mode full` for complete analysis."

    agents = routing_data.get("agents", [])
    if not agents:
        return "No agent files found."

    lines = ["| Subagent | Current Model | Recommended | Tools | Savings |"]
    lines.append("|---|---|---|---|---|")
    for agent in agents:
        tools_str = ", ".join(agent.get("tools", []))
        lines.append(
            f"| {agent['name']} | {agent['current_model']} | "
            f"{agent['recommended_model']} | {tools_str} | "
            f"{agent['estimated_savings']} |"
        )

    summary = routing_data.get("summary", {})
    mismatches = summary.get("total_mismatches", 0)
    desc = summary.get("potential_savings_description", "")
    if mismatches > 0:
        lines.append("")
        lines.append(f"**{mismatches} mismatch(es) detected.** {desc}")

    return "\n".join(lines)


def build_pollution_section(pollution_data):
    if not pollution_data:
        return "Not included in this mode. Run with `--mode full` for complete analysis."

    patterns = pollution_data.get("patterns_detected", [])
    if not patterns:
        return "No context pollution patterns detected."

    lines = ["| Pattern | Location | Tokens Injected | After Delegation | Saving/Turn |"]
    lines.append("|---|---|---|---|---|")
    for p in patterns:
        lines.append(
            f"| {p['type']} | {p['location']} | "
            f"{p['estimated_tokens_per_occurrence']:,} | "
            f"{p['estimated_summary_tokens']:,} | "
            f"{p['savings_per_turn']:,} |"
        )

    return "\n".join(lines)


def build_anti_patterns_section(structure_data):
    if not structure_data:
        return "No structural analysis available."

    anti_patterns = structure_data.get("anti_patterns", [])
    if not anti_patterns:
        return "No anti-patterns detected."

    lines = []
    for i, ap in enumerate(anti_patterns, 1):
        severity = ap.get("severity", "MEDIUM")
        pattern = ap.get("pattern", "unknown")
        detail = ap.get("detail", "")
        fix = ap.get("fix", "")
        lines.append(f"{i}. **[{severity}]** {pattern} - {detail} -> {fix}")

    return "\n".join(lines)


def build_cache_hygiene_section(cache_data):
    if not cache_data:
        return "Not included in this mode. Run with `--mode full` for complete analysis."

    findings = cache_data.get("findings", [])
    if not findings:
        return "No cache-busting patterns detected."

    lines = ["| # | Category | Severity | Detail | Fix |"]
    lines.append("|---|---|---|---|---|")
    for i, f in enumerate(findings, 1):
        lines.append(
            f"| {i} | {f['category']} | {f['severity']} | "
            f"{f['detail']} | {f['fix']} |"
        )

    summary = cache_data.get("summary", {})
    score = summary.get("cache_hygiene_score", "?")
    lines.append("")
    lines.append(f"**Cache hygiene score: {score}/10**")

    size_check = cache_data.get("cacheable_size_check", {})
    if not size_check.get("meets_haiku_sonnet_minimum"):
        tokens = size_check.get("skill_md_tokens", 0)
        lines.append("")
        lines.append(f"Note: SKILL.md body (~{tokens} tokens) is below the 1,024-token caching minimum for Haiku/Sonnet.")

    return "\n".join(lines)


def build_delegation_section(delegation_data):
    if not delegation_data:
        return "Not included in this mode. Run with `--mode full` for complete analysis."

    agents = delegation_data.get("agents_analyzed", [])
    skill_findings = delegation_data.get("skill_md_findings", [])

    if not agents and not skill_findings:
        return "No delegation pattern issues detected."

    lines = []

    if agents:
        lines.append("| Agent | maxTurns | Structured Response | Closest Template | Extra Tools | Findings |")
        lines.append("|---|---|---|---|---|---|")
        for a in agents:
            mt = str(a.get("max_turns_value", "missing")) if a.get("has_max_turns") else "MISSING"
            sr = "Yes" if a.get("has_structured_response") else "No"
            tmpl = a.get("closest_template", "none") or "none"
            extra = ", ".join(a.get("extra_tools", [])) or "-"
            finding_count = len(a.get("findings", []))
            lines.append(f"| {a['name']} | {mt} | {sr} | {tmpl} | {extra} | {finding_count} |")

    if skill_findings:
        lines.append("")
        for i, f in enumerate(skill_findings, 1):
            lines.append(f"{i}. **[{f['severity']}]** {f['category']} - {f['detail']} -> {f['fix']}")

    summary = delegation_data.get("summary", {})
    score = summary.get("delegation_hygiene_score", "?")
    lines.append("")
    lines.append(f"**Delegation hygiene score: {score}/10**")

    return "\n".join(lines)


def build_recommendations_table(structure_data, routing_data, pollution_data, cache_data, delegation_data):
    recommendations = []

    if pollution_data:
        for p in pollution_data.get("patterns_detected", []):
            recommendations.append({
                "action": f"Delegate {p['type']} to {p['recommended_delegation']}",
                "token_savings": p["savings_per_turn"],
                "effort": "LOW",
            })

    if routing_data:
        for agent in routing_data.get("agents", []):
            if not agent.get("is_optimised"):
                estimated_tokens = 2000
                recommendations.append({
                    "action": f"Set {agent['name']} model to {agent['recommended_model']}",
                    "token_savings": estimated_tokens,
                    "effort": "LOW",
                })

    if structure_data:
        for ap in structure_data.get("anti_patterns", []):
            savings_map = {
                "monolithic_skill_md": 5000,
                "no_progressive_disclosure": 4000,
                "inline_troubleshooting": 2000,
                "inline_examples_too_long": 1500,
            }
            token_savings = savings_map.get(ap.get("pattern", ""), 1000)
            effort_map = {
                "HIGH": "MED",
                "MEDIUM": "LOW",
                "LOW": "LOW",
            }
            recommendations.append({
                "action": ap.get("fix", "See anti-pattern details"),
                "token_savings": token_savings,
                "effort": effort_map.get(ap.get("severity", "MEDIUM"), "MED"),
            })

    if cache_data:
        severity_savings = {"HIGH": 5000, "MEDIUM": 2000, "LOW": 500}
        for f in cache_data.get("findings", []):
            if f["severity"] == "LOW":
                continue
            recommendations.append({
                "action": f["fix"],
                "token_savings": severity_savings.get(f["severity"], 1000),
                "effort": "MED" if f["severity"] == "HIGH" else "LOW",
            })

    if delegation_data:
        severity_savings = {"HIGH": 4000, "MEDIUM": 1500, "LOW": 500}
        all_findings = list(delegation_data.get("skill_md_findings", []))
        for agent in delegation_data.get("agents_analyzed", []):
            all_findings.extend(agent.get("findings", []))
        for f in all_findings:
            recommendations.append({
                "action": f.get("fix", "See delegation audit details"),
                "token_savings": severity_savings.get(f["severity"], 1000),
                "effort": "LOW",
            })

    recommendations.sort(key=lambda r: r["token_savings"], reverse=True)

    if not recommendations:
        return "| - | No recommendations | - | - |"

    lines = []
    for i, rec in enumerate(recommendations, 1):
        lines.append(
            f"| {i} | {rec['action']} | {rec['token_savings']:,} | {rec['effort']} |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a skill profiling report in markdown format."
    )
    parser.add_argument(
        "skill_dir",
        help="Path to the skill directory",
    )
    parser.add_argument(
        "--agents-dir",
        help="Path to the agents directory for model routing audit",
    )
    parser.add_argument(
        "--mode",
        choices=["static", "routing", "pollution", "cache", "delegation", "full"],
        default="full",
        help="Report mode (default: full)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read pre-computed JSON from stdin instead of running sub-scripts",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    if not skill_dir.is_dir():
        print(f"Error: not a directory: {args.skill_dir}", file=sys.stderr)
        sys.exit(1)

    skill_md_path = skill_dir / "SKILL.md"

    errors = []

    if args.stdin:
        try:
            stdin_data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON on stdin: {e}", file=sys.stderr)
            sys.exit(1)

        structure_data = stdin_data.get("analyze_structure")
        tokens_data = stdin_data.get("estimate_tokens")
        description_data = stdin_data.get("score_trigger_description")
        routing_data = stdin_data.get("audit_model_routing")
        pollution_data = stdin_data.get("scan_context_pollution")
        cache_data = stdin_data.get("audit_cache_hygiene")
        delegation_data = stdin_data.get("audit_delegation_patterns")
    else:
        structure_data, err = run_script("analyze_structure.py", [str(skill_dir)])
        if err:
            errors.append(f"analyze_structure: {err}")

        tokens_data, err = run_script("estimate_tokens.py", [str(skill_dir)])
        if err:
            errors.append(f"estimate_tokens: {err}")

        description_text = ""
        if skill_md_path.exists():
            content = skill_md_path.read_text(encoding="utf-8", errors="replace")
            fm = parse_frontmatter(content)
            description_text = fm.get("description", "")

        description_data = None
        if description_text:
            desc_result, err = run_script(
                "score_trigger_description.py",
                ["--description", description_text],
            )
            if err:
                errors.append(f"score_trigger_description: {err}")
            else:
                description_data = desc_result
        else:
            errors.append("score_trigger_description: no description found in SKILL.md frontmatter")

        routing_data = None
        if args.mode in ("routing", "full") and args.agents_dir:
            routing_data, err = run_script("audit_model_routing.py", [args.agents_dir])
            if err:
                errors.append(f"audit_model_routing: {err}")

        pollution_data = None
        if args.mode in ("pollution", "full") and skill_md_path.exists():
            pollution_data, err = run_script("scan_context_pollution.py", [str(skill_md_path)])
            if err:
                errors.append(f"scan_context_pollution: {err}")

        cache_data = None
        if args.mode in ("cache", "full"):
            cache_data, err = run_script("audit_cache_hygiene.py", [str(skill_dir)])
            if err:
                errors.append(f"audit_cache_hygiene: {err}")

        delegation_data = None
        if args.mode in ("delegation", "full"):
            deleg_args = [str(skill_dir)]
            if args.agents_dir:
                deleg_args.extend(["--agents-dir", args.agents_dir])
            delegation_data, err = run_script("audit_delegation_patterns.py", deleg_args)
            if err:
                errors.append(f"audit_delegation_patterns: {err}")

    skill_name = "unknown"
    if structure_data:
        skill_name = structure_data.get("skill_name", "unknown")
    elif skill_md_path.exists():
        content = skill_md_path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(content)
        skill_name = fm.get("name", skill_dir.name)
    else:
        skill_name = skill_dir.name

    overall_score = calculate_overall_score(
        structure_data, description_data, routing_data, pollution_data,
        cache_data, delegation_data
    )

    struct = structure_data.get("structure", {}) if structure_data else {}
    body_lines = struct.get("body_lines", 0)
    body_estimated_tokens = struct.get("body_estimated_tokens", 0)
    frontmatter_tokens = struct.get("frontmatter_tokens", 0)
    refs_count = struct.get("references_count", 0)
    scripts_count_val = struct.get("scripts_count", 0)

    desc_quality = structure_data.get("description_quality", {}) if structure_data else {}
    desc_score_val = desc_quality.get("quality_score", 0)
    if description_data and "total_score" in description_data:
        desc_score_val = description_data["total_score"]

    total_token_savings = 0
    if pollution_data:
        total_token_savings += pollution_data.get("total_estimated_waste_per_session", 0)

    anti_patterns_list = []
    if structure_data:
        anti_patterns_list = structure_data.get("anti_patterns", [])

    priority_count = len(anti_patterns_list)
    if pollution_data:
        priority_count += pollution_data.get("total_patterns", 0)
    if routing_data:
        priority_count += routing_data.get("summary", {}).get("total_mismatches", 0)
    if cache_data:
        priority_count += cache_data.get("summary", {}).get("high", 0)
        total_token_savings += cache_data.get("summary", {}).get("high", 0) * 5000
    if delegation_data:
        priority_count += delegation_data.get("summary", {}).get("high", 0)
        summary = delegation_data.get("summary", {})
        total_token_savings += summary.get("agents_without_structured_response", 0) * 1500

    cumulative_token_savings = total_token_savings

    template_path = TEMPLATE_PATH.resolve()
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        errors.append(f"Template not found: {template_path}")
        template = "# Skill Profile Report: {{skill_name}}\n\n{{errors}}"

    bl_status = status_indicator(body_lines, body_lines_status)
    bt_status = status_indicator(body_estimated_tokens, body_tokens_status)
    ft_status = status_indicator(frontmatter_tokens, frontmatter_tokens_status)

    ref_result = references_status(refs_count, body_lines)
    ref_status_str = "PASS" if ref_result == "pass" else "FAIL"

    sc_result = scripts_status(scripts_count_val)
    sc_status_str = "PASS" if sc_result == "pass" else "WARN"

    ds_status = status_indicator(desc_score_val, description_score_status)

    model_routing_section = build_model_routing_section(routing_data)
    context_pollution_section = build_pollution_section(pollution_data)
    cache_hygiene_section = build_cache_hygiene_section(cache_data)
    delegation_section = build_delegation_section(delegation_data)
    anti_patterns_section = build_anti_patterns_section(structure_data)
    recommendations_table = build_recommendations_table(
        structure_data, routing_data, pollution_data, cache_data, delegation_data
    )

    if args.mode == "full":
        artefacts_lines = []
        artefacts_lines.append("- [ ] Optimised SKILL.md")
        artefacts_lines.append("- [ ] New subagent definitions (.md files)")
        artefacts_lines.append("- [ ] Extracted reference files")
        artefacts_lines.append("- [ ] Updated description")
        generated_artefacts_section = "\n".join(artefacts_lines)
    else:
        generated_artefacts_section = "Not included in this mode. Run with `--mode full` for auto-refactor artefacts."

    replacements = {
        "{{skill_name}}": skill_name,
        "{{overall_score}}": str(overall_score),
        "{{total_token_savings}}": f"{total_token_savings:,}",
        "{{priority_action_count}}": str(priority_count),
        "{{body_lines}}": str(body_lines),
        "{{body_lines_status}}": bl_status,
        "{{body_estimated_tokens}}": f"{body_estimated_tokens:,}",
        "{{body_tokens_status}}": bt_status,
        "{{frontmatter_tokens}}": str(frontmatter_tokens),
        "{{frontmatter_tokens_status}}": ft_status,
        "{{references_count}}": str(refs_count),
        "{{references_status}}": ref_status_str,
        "{{scripts_count}}": str(scripts_count_val),
        "{{scripts_status}}": sc_status_str,
        "{{description_score}}": str(desc_score_val),
        "{{description_status}}": ds_status,
        "{{model_routing_section}}": model_routing_section,
        "{{context_pollution_section}}": context_pollution_section,
        "{{cumulative_token_savings}}": f"{cumulative_token_savings:,}",
        "{{cache_hygiene_section}}": cache_hygiene_section,
        "{{delegation_section}}": delegation_section,
        "{{anti_patterns_section}}": anti_patterns_section,
        "{{recommendations_table}}": recommendations_table,
        "{{agentic_review_section}}": "Agentic review findings are added by the profiler agent after script analysis.",
        "{{generated_artefacts_section}}": generated_artefacts_section,
    }

    report = template
    for marker, value in replacements.items():
        report = report.replace(marker, value)

    if errors:
        error_section = "\n\n## Errors\n\n"
        for e in errors:
            error_section += f"- {e}\n"
        report += error_section

    print(report)


if __name__ == "__main__":
    main()
