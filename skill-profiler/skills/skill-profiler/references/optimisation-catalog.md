# Optimisation Catalog

Organised into six categories by domain.

---

## 1. Structural Optimisations

| Technique | Detection Method | Expected Savings | Effort |
|---|---|---|---|
| Move detailed docs to `references/` | SKILL.md body >500 lines or >10,000 estimated tokens | 30-50% initial load reduction | Low |
| Keep SKILL.md under 500 lines | Line count check | Prevents context bloat | Low |
| Use scripts for deterministic validation | Instructions containing "verify", "check", "validate" without corresponding scripts/ entry | More reliable + fewer instruction tokens | Medium |
| Compress examples to minimal working form | Example blocks >20 lines | 10-20% body reduction | Low |
| Use `[REFERENCE.md](reference)` linking pattern | Inline content that isn't core workflow | On-demand loading only | Low |
| Remove inline troubleshooting | Troubleshooting section in body >30 lines | Move to references/troubleshooting.md | Low |
| Tighten frontmatter description | Description >800 chars or missing trigger phrases | Better trigger accuracy | Low |
| Add negative triggers to description | No "Do NOT use" clause present | Reduces false positive triggers | Low |
| Use `.claudeignore` for historical directories | `.claude/completions/`, `sessions/` dirs exist without `.claudeignore` | Prevents auto-loading of historical context | Low |

---

## 2. Model Routing Optimisations

| Technique | Detection Method | Expected Savings | Effort |
|---|---|---|---|
| Route file exploration to Haiku subagents | Subagent with tools: Read, Grep, Glob and no `model:` field or `model: inherit` | 5-10x (96-97% per-task reduction) | Low |
| Route test execution to Haiku subagents | Subagent running test commands via Bash | 5-10x cheaper, results stay out of main context | Low |
| Set explicit `model: haiku` on read-only subagents | Any subagent with only read-only tools and model not set to haiku | Prevents inheriting expensive parent model | Trivial |
| Use Sonnet for implementation, Opus only for planning/architecture | Subagent doing code writing/editing with `model: opus` | ~5x cheaper for implementation steps | Low |
| Use opusplan mode for complex refactoring | Agent doing both planning and implementation on Opus | Opus-quality plans, Sonnet-speed execution | Low |
| Route data fetching (MCP tool calls) to Haiku subagents | Subagent calling MCP tools for data gathering | 5-10x cheaper, structured returns | Medium |
| Route documentation research to Haiku/Sonnet subagents | Operations involving WebFetch/WebSearch | Keeps fetched pages out of main context | Low |

---

## 3. Context Pollution Optimisations

| Technique | Detection Method | Expected Savings | Effort |
|---|---|---|---|
| Delegate sequential file reads to Explore subagent | >3 consecutive Read tool calls in skill instructions | Eliminates stale file content from main context | Low |
| Filter MCP responses through extraction subagent | Skill calls MCP tools that return >1,000 tokens | 90-98% reduction for large MCP outputs | Medium |
| Run tests in subagent, return failures only | Bash tool calls executing test suites | Eliminates hundreds of lines of passing test output | Low |
| Delegate documentation research to subagent | WebFetch/WebSearch tool sequences | Keeps fetched pages out of main context | Low |
| Use structured return schemas for subagent results | Subagents returning unstructured narrative | Ensures concise, parseable returns | Low |
| Write large tool outputs to temp files, read summary | MCP/Bash output >2,000 tokens staying in context | Main agent reads metadata, not raw data | Medium |
| Batch related reads into single subagent invocation | Multiple separate subagent spawns for related reads | One spawn overhead covers multiple reads | Medium |

| Use dynamic toolset / 3-meta-tool pattern | MCP server with >20 tool definitions always loaded | 96.7% input token reduction for large MCP toolsets | Medium |
| Delegate parallel tool calls within subagents | >2 independent tool calls executed sequentially | 90% latency reduction via parallel execution | Low |

**Break-even rule**: Delegate when expected tool output >1,500 tokens, or when >3 sequential tool calls would occur in the main thread. Below this threshold, the subagent spawn overhead (~500-1,000 tokens for system prompt + tool definitions) exceeds the savings.

---

## 4. Runtime Optimisations

| Technique | Detection Method | Expected Savings | Effort |
|---|---|---|---|
| Enable token-efficient tool use beta header | Not using `anthropic-beta: token-efficient-tools-2025-02-19` | ~14% average output token savings, up to 70% | Trivial |
| Optimise prompt caching layout (static content first) | Dynamic content before static in prompt structure | Up to 90% token reduction on cached reads | Medium |
| Use 1-hour cache TTL for longer sessions | Using default 5-min TTL when requests are >5 min apart | Avoids repeated cache writes | Low |
| Batch related operations in single tool calls | Multiple individual tool calls for related data | Fewer round-trips, less overhead | Medium |
| Specific prompts over vague instructions | Instructions containing "handle appropriately", "process as needed" | Fewer exploratory file reads, less scanning | Low |
| Use `/compact` with targeted preservation instructions | Long sessions without compaction guidance | Preserves important context during summarisation | Low |
| Prefer CLI tools over MCP servers when possible | MCP server used where equivalent CLI exists (gh, aws, gcloud) | Eliminates persistent tool definition overhead | Low |
| Use `--print` / headless mode for automated workflows | Interactive mode used in CI/CD or scripted contexts | Significantly fewer tokens than interactive sessions | Low |
| Fork session (`--fork-session`) for parallel context sharing | Multiple independent tasks needing shared base context | 1.55x vs 3.75x token multiplier | Low |
| External memory pattern (NOTES.md/TODO.md) | Multi-session skill with >10 steps, no state file writes | 39% better task performance, survives compaction | Low |

---

## 5. Systemic / Portfolio Optimisations

| Technique | Detection Method | Expected Savings | Effort |
|---|---|---|---|
| Reduce simultaneously enabled skills | >20 skills enabled, many rarely triggered | ~100 tokens saved per disabled skill frontmatter | Low |
| Consolidate overlapping skills | Multiple skills with similar trigger descriptions | Eliminates redundant context loading | Medium |
| Session-start hooks for dynamic context loading | Large CLAUDE.md loading everything upfront | 60%+ context reduction per session | Medium |
| Skill "packs" (enable/disable groups by domain) | Skills from different domains all enabled simultaneously | Contextual loading only | Medium |
| Fleet-wide model routing policy | Inconsistent model assignment across subagents | Uniform token optimisation | Medium |
| Use hierarchical CLAUDE.md files | Single monolithic CLAUDE.md >500 lines | Load only domain-relevant section | Medium |

---

## 6. Environment & Settings

| Technique | Detection Method | Expected Savings | Effort |
|---|---|---|---|
| Set `MAX_THINKING_TOKENS` to limit thinking budget | Extended thinking enabled without token cap | 70% thinking token reduction | Trivial |
| Set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Long sessions without manual compaction threshold | Tunable automatic compaction trigger | Trivial |
| Set `CLAUDE_CODE_SUBAGENT_MODEL=haiku` | Exploration subagents inheriting expensive parent model | 80% exploration token reduction | Trivial |

