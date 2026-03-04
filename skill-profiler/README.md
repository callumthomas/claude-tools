# skill-profiler

A Claude Code skill that profiles and optimises other skills and agent configurations for token efficiency, model routing, and context management.

## Usage

Invoke in Claude Code:

```
/skill-profiler path/to/skill-dir
```

Or with agents:

```
/skill-profiler path/to/skill-dir --agents-dir ~/.claude/agents/
```

## Modes

| Mode | Trigger | What it covers |
|---|---|---|
| Static Analysis | default | Structure, tokens, description quality, anti-patterns |
| Model Routing | "check model routing" | Static + subagent model classification |
| Context Pollution | "reduce context pollution" | Static + read-heavy pattern detection |
| Full Profile | "full profile" | All of the above, deduplicated |
| Auto-Refactor | "optimise this skill" | Full profile + generates optimised files |

`--deep` can be added to any mode for an additional semantic analysis pass by the agent.

## Scripts

All scripts are standalone Python 3 (stdlib only) and output JSON to stdout.

| Script | Input | Purpose |
|---|---|---|
| `analyze_structure.py <skill-dir>` | Skill directory | Structural analysis, anti-pattern detection |
| `estimate_tokens.py <path>` | File or directory | Token count estimates per file |
| `score_trigger_description.py --description <text> [--others <text>...]` | Description string | Description quality scoring, collision detection |
| `audit_model_routing.py <agents-dir>` | Agents directory | Model routing mismatch detection |
| `scan_context_pollution.py <skill.md>` | SKILL.md file | Read-heavy pattern detection |
| `generate_report.py <skill-dir> [flags]` | Skill directory | Assembles full markdown report |

### generate_report.py flags

```
--agents-dir PATH    Agents directory for model routing audit
--mode MODE          static | routing | pollution | full (default: full)
--stdin              Read pre-computed JSON from stdin
```

## Examples

### In Claude Code (natural language)

```
# Static analysis (default)
/skill-profiler ~/.claude/skills/my-skill/

# Full profile
/skill-profiler ~/.claude/skills/my-skill/ full profile

# Model routing audit
/skill-profiler ~/.claude/skills/my-skill/ --agents-dir ~/.claude/agents/ check model routing

# Context pollution scan
/skill-profiler ~/.claude/skills/my-skill/ reduce context pollution

# Auto-refactor (generates optimised files with approval)
/skill-profiler ~/.claude/skills/my-skill/ optimise this skill

# Any mode + deep semantic analysis
/skill-profiler ~/.claude/skills/my-skill/ --deep
/skill-profiler ~/.claude/skills/my-skill/ full profile --deep
```

### Scripts directly

Static analysis only:

```sh
python3 skill-profiler/skills/skill-profiler/scripts/generate_report.py ~/.claude/skills/my-skill/ --mode static
```

Full profile with agents:

```sh
python3 skill-profiler/skills/skill-profiler/scripts/generate_report.py ~/.claude/skills/my-skill/ \
  --agents-dir ~/.claude/agents/ --mode full
```

Context pollution scan only:

```sh
python3 skill-profiler/skills/skill-profiler/scripts/generate_report.py ~/.claude/skills/my-skill/ --mode pollution
```

Model routing audit only:

```sh
python3 skill-profiler/skills/skill-profiler/scripts/generate_report.py ~/.claude/skills/my-skill/ \
  --agents-dir ~/.claude/agents/ --mode routing
```

Self-profile:

```sh
python3 skill-profiler/skills/skill-profiler/scripts/generate_report.py skill-profiler/skills/skill-profiler/
```
