# Model Routing Guide

**Compatibility**: `model:` field routing only works in Claude Code and Agent SDK, not Claude.ai skills.

---

## Task Classification Framework

### Tier 1 -- Haiku-eligible

Clear input/output, no judgment required.

- File reading, grep/glob searches, codebase exploration
- Data extraction from structured formats (JSON, CSV, YAML)
- Simple text formatting, template filling
- Running tests and collecting output
- Log parsing and filtering
- Status checks and pattern-matching validation
- Documentation lookup and retrieval
- Metrics collection from APIs

### Tier 2 -- Sonnet-eligible

Pattern recognition, synthesis, judgment.

- Code implementation from clear specifications
- Code review with known criteria
- Data analysis and summarisation
- Writing/editing with style guidelines
- Test generation
- Bug fixing with clear reproduction steps
- Multi-file refactoring with defined rules
- PR/commit message generation

### Tier 3 -- Opus-required

Novel reasoning, ambiguity, architecture.

- Architectural decisions with tradeoffs
- Complex debugging with unclear root causes
- Strategic planning and prioritisation
- Security analysis requiring creative threat modelling
- Cross-domain synthesis with ambiguous requirements
- Workflow orchestration and high-level coordination
- Novel algorithm design

---

## Decision Tree

```
START: Classify the subagent's primary task
  |
  +-- Does the task require novel reasoning, architectural decisions,
  |   or handling significant ambiguity?
  |     |
  |     YES --> Tier 3: model: opus
  |     |
  |     NO
  |       |
  |       +-- Does the task require judgment, synthesis, code writing,
  |       |   or pattern recognition beyond simple extraction?
  |       |     |
  |       |     YES --> Tier 2: model: sonnet
  |       |     |
  |       |     NO
  |       |       |
  |       |       +-- Is the task primarily:
  |       |           reading, searching, extracting, formatting,
  |       |           running commands, or collecting output?
  |       |             |
  |       |             YES --> Tier 1: model: haiku
  |       |             |
  |       |             NO --> Default to Tier 2: model: sonnet
```

---

## Relative Model Token Cost

| Model | Relative Token Cost |
|---|---|
| Haiku | 1x (baseline) |
| Sonnet | ~3.75x |
| Opus | ~18.75x |

---

## Examples

### Correctly Routed

| Task | Model | Reasoning |
|---|---|---|
| Scan codebase for all `.ts` files importing a specific module | haiku | Pure grep/glob search with structured output |
| Run `pytest` and return failure summary | haiku | Command execution + output parsing, no judgment |
| Implement a REST endpoint from an OpenAPI spec | sonnet | Code generation from clear specification |
| Review PR diff for style guide violations | sonnet | Pattern recognition against known criteria |
| Design a caching architecture for a distributed system | opus | Novel architecture with multiple tradeoffs |
| Debug an intermittent race condition with no reproduction steps | opus | Complex reasoning under ambiguity |

### Incorrectly Routed

| Task | Current Model | Should Be | Problem |
|---|---|---|---|
| Read 5 config files and summarise their contents | opus (inherit) | haiku | Inheriting parent Opus model for a simple read task; 18.75x token overhead |
| Search for all TODO comments in the codebase | sonnet | haiku | No judgment required; 3.75x token overhead |
| Fetch API docs via WebFetch and extract relevant sections | opus (inherit) | haiku | Data retrieval and filtering; expensive model wasted on extraction |
| Write a complex migration strategy across 3 services | haiku | sonnet or opus | Task requires synthesis and judgment; haiku likely to produce poor results |

---

## When `inherit` Is Acceptable

Acceptable only when the parent is already on the appropriate model for this subagent's task tier.

In practice, `inherit` is almost never optimal — parent agents run Sonnet/Opus for orchestration, but most subagent tasks are Tier 1 Haiku-eligible.

**Default**: Always set an explicit `model:` field on every subagent.
