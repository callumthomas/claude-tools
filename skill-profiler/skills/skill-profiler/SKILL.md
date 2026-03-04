---
name: skill-profiler
description: >
  Analyse and optimise Claude skills and agent configurations for token
  efficiency, model routing, and context management. Use when user says
  "profile this skill", "optimise this agent", "audit token usage",
  "check model routing", "reduce context pollution", "analyse skill
  efficiency", or "run profiler". Also use when user uploads or references
  a SKILL.md file and asks about its efficiency, token usage, or structure.
  Do NOT use for general code profiling, application performance, or
  non-skill optimisation tasks.
disable-model-invocation: true
---

# Skill Profiler

Analyse, profile, and optimise Claude Code skills and agent configurations. Produces structured profiling reports with token savings estimates, model routing recommendations, and context pollution fixes. Can auto-refactor skills with user approval.

## Profiling Modes

| Mode | Trigger | What it does |
|---|---|---|
| **Static Analysis** (default) | "profile this skill", "analyse structure" | Structure, tokens, description quality, anti-patterns |
| **Model Routing Audit** | "check model routing", "audit agents" | All of Static + subagent model classification, mismatch detection, delegation pattern audit |
| **Context Pollution Scan** | "reduce context pollution", "check context waste" | All of Static + read-heavy pattern detection, delegation recommendations, cache hygiene audit |
| **Cache Hygiene** | "check caching", "audit cache patterns" | All of Static + cache-busting pattern detection |
| **Delegation Audit** | "check delegation", "audit delegation patterns" | All of Static + agent delegation template compliance |
| **Full Profile** | "full profile", "run profiler" | All modes combined, deduplicated, priority-ranked |
| **Auto-Refactor** | "optimise this skill", "auto-refactor" | Full Profile + generates optimised files with user approval |

When the user's intent is ambiguous, default to **Full Profile**.

## Script Location

This skill's Python scripts are in the `scripts/` subdirectory relative to this SKILL.md file. Resolve the absolute path from this file's location. All script invocations below use `<profiler-scripts>` to refer to that directory. This is distinct from `<target-skill-dir>`, which is the skill being profiled.

## Workflow

### Step 1: Intake

Gather the target skill/agent files:

1. If the user provides a path, use it directly
2. If they name a skill, search for it:
   - `~/.claude/skills/<name>/SKILL.md`
   - `.claude/skills/<name>/SKILL.md`
   - Current directory if it contains a SKILL.md
3. If profiling agents, also locate:
   - `~/.claude/agents/` directory
   - `.claude/agents/` directory
4. Confirm the target with the user before proceeding

Ask the user which surface they're targeting if model routing or delegation recommendations are needed:
- **Claude Code**: Full support (subagents, model routing, scripts)
- **Agent SDK**: Full support (programmatic)
- **Claude.ai**: Partial (no subagent model routing or delegation)
- **API**: Full support with manual configuration

### Step 2: Static Analysis

Run the structural analysis script:

```bash
python3 <profiler-scripts>/analyze_structure.py <target-skill-dir>
```

This checks:
- SKILL.md exists with correct casing
- Folder naming (kebab-case)
- No README.md in skill folder
- YAML frontmatter validity (no XML angle brackets)
- Body line count and estimated token count
- References and scripts directory presence
- Inline sections that should be in references/ (troubleshooting >30 lines, examples >20 lines)
- Progressive disclosure compliance

Also run token estimation:

```bash
python3 <profiler-scripts>/estimate_tokens.py <target-skill-dir>
```

And score the description:

```bash
python3 <profiler-scripts>/score_trigger_description.py --description "<description text>"
```

For collision detection, pass other skill descriptions:

```bash
python3 <profiler-scripts>/score_trigger_description.py --description "<desc>" --others "<desc2>" "<desc3>"
```

**Agentic Validation** (rubric sections 2, 3, 5 — see [validation-rubric.md](references/validation-rubric.md)):

After the scripts return, read the target SKILL.md body and the script output, then validate:

- Check anti-pattern findings for false positives (e.g. "always confirm" is a safety requirement, not bad prompting)
- Check for false negatives the regex missed (implicit iteration, unrestricted tool scope, duplicate instructions)
- Assess description effectiveness beyond keyword scoring — do trigger phrases match natural user phrasing? Are negative triggers missing for common false-activation scenarios?
- Check instruction coherence: contradictions, missing error handling, loop risks, implicit assumptions
- Note corrections to feed into the report

### Step 3: Model Routing Audit

**Modes 2, 4, 5 only.** Skip for Static Analysis and Context Pollution modes.

Run the model routing audit:

```bash
python3 <profiler-scripts>/audit_model_routing.py <agents-dir>
```

This classifies each agent by tool permissions and recommends the appropriate model tier:

- **Haiku**: Read-only tools (Read, Grep, Glob), data extraction, test running, log parsing
- **Sonnet**: Code implementation, code review, test generation, multi-file refactoring
- **Opus**: Architecture decisions, complex debugging, strategic planning, security analysis

Also scan the SKILL.md body for operations that imply model needs but happen in the main thread instead of being delegated. Cross-reference with Step 4 findings.

For detailed tier classification, see [model-routing-guide.md](references/model-routing-guide.md).

Also run the delegation patterns audit:

```bash
python3 <profiler-scripts>/audit_delegation_patterns.py <target-skill-dir> [--agents-dir <agents-dir>]
```

This checks agent files against the delegation templates in [delegation-patterns.md](references/delegation-patterns.md):
- Missing maxTurns on agent files
- Missing structured response format guidance
- Overly broad tool sets that don't match any delegation template
- Break-even violations (trivially small delegated tasks)
- maxTurns values mismatched to task complexity

**Agentic Validation** (rubric section 4 — see [validation-rubric.md](references/validation-rubric.md)):

After the scripts return, read each agent's actual instructions (not just frontmatter) and validate:

- Check if tool-based model classification matches the cognitive complexity of the task
- Flag misleading tool presence (e.g. Bash used only for `grep` → Haiku is fine)
- Flag tasks requiring reasoning beyond what tools suggest (read-only tools but architectural analysis needed)
- Validate delegation template matches — does the agent actually follow the template pattern?

### Step 4: Context Pollution Scan

**Modes 3, 4, 5 only.** Skip for Static Analysis and Model Routing modes.

Run the context pollution scanner:

```bash
python3 <profiler-scripts>/scan_context_pollution.py <target-skill-md-path>
```

This detects:
- Sequential file read patterns (>3 consecutive Read/Bash calls)
- Unfiltered MCP tool responses (>1,000 token outputs)
- Test execution in the main thread
- Documentation fetching without subagent delegation
- Log analysis in the main thread

Apply the break-even rule: only recommend delegation when expected tool output exceeds 1,500 tokens or when more than 3 sequential tool calls would occur. Below this threshold, subagent spawn overhead (~500-1,000 tokens) exceeds the savings.

For delegation templates, see [delegation-patterns.md](references/delegation-patterns.md).

Also run the cache hygiene audit:

```bash
python3 <profiler-scripts>/audit_cache_hygiene.py <target-skill-dir>
```

This detects cache-busting patterns from [cache-strategies.md](references/cache-strategies.md):
- Timestamps or dynamic content in system prompts/tool definitions
- Instructions to add/remove MCP tools mid-session
- Dynamic content placed before static content in prompt structure
- Model switching mid-session (invalidates per-model cache)
- Content below minimum cacheable token thresholds

**Agentic Validation** (rubric section 1 — see [validation-rubric.md](references/validation-rubric.md)):

After the scripts return, read the SKILL.md body and validate:

- Look for context pollution the regex missed
- Identify sequential reads without parallelisation that aren't flagged
- Identify large unsummarised tool outputs
- Identify multi-step processing chains where intermediate results inflate context
- Validate cache-busting findings — is the "dynamic content" actually in a system prompt, or is it in a user message where it's fine?

### Step 5: Generate Recommendations

Aggregate findings from all completed steps, including agentic validation corrections:

1. Deduplicate across modes (e.g., a subagent with `model: inherit` and read-only tools is both a routing and pollution issue)
2. Incorporate agentic validation results — remove false positives, add false negatives
3. Priority-rank by: `(token_savings × frequency) / effort`
4. Estimate savings using the evidence base in [optimisation-catalog.md](references/optimisation-catalog.md)
5. For Claude.ai targets, filter out subagent model routing and delegation recommendations

Each recommendation must include:
- What to change
- Expected token savings
- Effort level (LOW / MEDIUM / HIGH)
- Which reference file has the detailed technique

Consolidate all agentic validation findings into a single "Agentic Review" section for the report. Present findings as a numbered list with severity, finding, and recommendation — same format as Anti-Patterns. Replace the `## Agentic Review` placeholder in the report with the findings.

### Step 6: Auto-Refactor

**Auto-Refactor mode only.** Skip for all other modes.

Present the full report from Step 5 and ask the user which recommendations to apply. Do NOT auto-apply without explicit confirmation.

For each approved recommendation:

- **Structural**: Rewrite SKILL.md body, extract sections to `references/` files
- **Model routing**: Generate new subagent `.md` files with correct model fields using templates from [delegation-patterns.md](references/delegation-patterns.md)
- **Context delegation**: Generate subagent `.md` files for read-heavy operations
- **Description**: Rewrite description with trigger phrases and negative triggers

Output all generated files for the user to review before writing to disk.

### Step 7: Validation

Generate the final report:

```bash
python3 <profiler-scripts>/generate_report.py <target-skill-dir> [--agents-dir <path>] [--mode full]
```

For Auto-Refactor mode, run the full pipeline again on the optimised version and present a before/after comparison showing:
- Token count changes per tier (L1, L2, L3)
- Model routing improvements
- Context pollution reduction
- Overall efficiency score change

Quality gate for auto-refactored output:
- SKILL.md must remain under 500 lines
- Frontmatter must parse cleanly
- Description must score 7+ on quality
- No new HIGH severity anti-patterns introduced

## Output Format

The profiler produces a structured markdown report. See [report-template.md](assets/report-template.md) for the full template.

Key sections: Summary (score + savings), Structural Analysis (metrics table), Model Routing Audit (agent table), Context Pollution Scan (pattern table), Cache Hygiene Audit (cache-busting findings), Delegation Patterns Audit (agent compliance table), Anti-Patterns Detected (severity-ranked list), Recommendations (impact-ranked table), Agentic Review (consolidated validation findings), Generated Artefacts (if auto-refactor).

## Surface Compatibility

| Feature | Claude Code | Agent SDK | Claude.ai | API |
|---|---|---|---|---|
| Structural analysis | Yes | Yes | Yes | Yes |
| Description tuning | Yes | Yes | Yes | Yes |
| Progressive disclosure | Yes | Yes | Yes | Yes |
| Model routing audit | Yes | Yes | No | Yes |
| Subagent delegation | Yes | Yes | No | Yes |
| Script execution | Yes | Yes | No | Yes |
| Auto-refactor | Yes | Yes | Partial | Yes |

Adjust recommendations based on the user's target surface. Never recommend subagent model routing for Claude.ai users.

## Important

- Always show the report before any auto-refactoring
- Never auto-apply changes without explicit user confirmation
- Express all savings and efficiency metrics in tokens, never in dollar amounts
- Conservative model downgrade recommendations only — suggest Haiku only for clear Tier 1 tasks
- When unsure about a model recommendation, suggest Sonnet as the safe default
- For detailed optimisation techniques, see [optimisation-catalog.md](references/optimisation-catalog.md)
- For known anti-patterns, see [anti-patterns.md](references/anti-patterns.md)
- For cache optimisation guidance, see [cache-strategies.md](references/cache-strategies.md)
- For progressive disclosure patterns, see [progressive-disclosure-guide.md](references/progressive-disclosure-guide.md)
- Validate the profiler itself by running it against its own directory
