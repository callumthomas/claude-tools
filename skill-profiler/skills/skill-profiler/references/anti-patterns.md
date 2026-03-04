# Anti-Patterns Detection Reference

## Detection Heuristic Table

| # | Anti-Pattern | Detection Heuristic | Severity |
|---|---|---|---|
| 1 | Monolithic SKILL.md | Body >500 lines or >10,000 estimated tokens | HIGH |
| 2 | No progressive disclosure | 0 files in references/ when body >300 lines | HIGH |
| 3 | Subagents inheriting parent model | Subagent .md files with no `model:` field or `model: inherit` | HIGH |
| 4 | Read-heavy main thread | Skill instructions with >3 sequential Read/Bash/WebFetch calls without subagent delegation | HIGH |
| 5 | Large MCP responses unfiltered | Skill calls MCP tools without filtering/summarising output | HIGH |
| 6 | Cache-busting patterns | Dynamic content (timestamps, random IDs) in system prompt or tool definitions | HIGH |
| 7 | Vague description | Description <100 chars or missing "Use when" clause | MEDIUM |
| 8 | Missing negative triggers | No "Do NOT use" / exclusion clause in description | MEDIUM |
| 9 | Inline troubleshooting | Troubleshooting section >30 lines in SKILL.md body | MEDIUM |
| 10 | Inline examples too long | Example blocks >20 lines each, or >3 example blocks | MEDIUM |
| 11 | All logic in instructions | No scripts/ directory when skill involves validation or data processing | MEDIUM |
| 12 | Test execution in main thread | Bash calls running test suites directly (not in subagent) | MEDIUM |
| 13 | Too many skills enabled | User reports >20 skills enabled simultaneously | MEDIUM |
| 14 | Description collision | Two or more skills with >60% keyword overlap in descriptions | MEDIUM |
| 15 | Vague instructions | Phrases like "handle appropriately", "process as needed", "do the right thing" | LOW |
| 16 | No error handling | No mention of failure recovery, retries, or error cases | LOW |
| 17 | No maxTurns on iterative subagents | "retry until" / "keep working until" without maxTurns | HIGH |
| 18 | Hard constraints via prompting instead of hooks | "do not delete", "always confirm before" in instructions | MEDIUM |
| 19 | Long-running skill without external memory | Multi-session / >10 steps, no state file write | HIGH |
| 20 | Historical dirs without .claudeignore | `.claude/completions/`, `sessions/` exist, no `.claudeignore` | MEDIUM |
| 21 | Sequential independent tool calls | "then" connecting parallelisable queries | LOW |
| 22 | Fast mode in non-interactive context | Fast mode in CI/CD or background workflows | HIGH |

## Severity Definitions

**HIGH** -- Directly causes significant token waste, incorrect model billing, or context window exhaustion. Should be fixed immediately.

**MEDIUM** -- Causes measurable inefficiency or increases risk of misrouting/misfiring. Should be addressed in the next iteration.

**LOW** -- Minor inefficiency or best-practice deviation. Fix when convenient.

## Usage

Check each heuristic in order. Zero HIGH findings and <3 MEDIUM findings = well-structured.
