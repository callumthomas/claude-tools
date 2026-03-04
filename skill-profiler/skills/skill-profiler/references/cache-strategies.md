# Cache Strategies

---

## Cache Hierarchy

Prompt caching uses strict prefix-matching:

```
tools --> system --> messages
```

Changes in an earlier layer invalidate all subsequent layers.

---

## Cache Breakpoint Placement

Up to 4 cache breakpoints per request:

1. After tool definitions (stable across requests)
2. After the system prompt / CLAUDE.md content (stable within a session)
3. After skill instructions loaded into system context (stable once loaded)
4. At the end of static message history (before the latest user message)

**Principle**: Static content first, dynamic content last.

---

## TTL Options

| TTL | Cache Write Multiplier | Cache Read Multiplier | Use When |
|---|---|---|---|
| 5 minutes (default) | 1.25x base input tokens | 0.1x base input tokens | Requests are <5 min apart (interactive sessions) |
| 1 hour (extended) | 2x base input tokens | 0.1x base input tokens | Requests are >5 min apart, or batch/async workflows |

5-minute TTL refreshes on each hit. 1-hour TTL avoids repeated writes when spacing is unpredictable.

---

## Minimum Cacheable Sizes

| Model | Minimum Tokens for Caching |
|---|---|
| Haiku | 1,024 tokens |
| Sonnet | 1,024 tokens |
| Opus | 2,048-4,096 tokens |

Content below these thresholds will not be cached.

---

## Token Usage Comparison

For a 20-turn session with 100K tokens of stable context (system prompt + tool definitions + skill instructions):

| Scenario | Effective Input Tokens per Turn |
|---|---|
| No caching | 100% of 100K tokens counted each turn |
| With caching | ~16% (0.1x on cached portion + full rate on new content) |

---

## Things That Break the Cache

- **Adding or removing MCP tools**
- **Timestamps in system prompt**
- **Switching models mid-session** -- each model has its own cache
- **Changing tool definitions**
- **Modifying images in prompts**
- **Reordering tools or system prompt sections** -- prefix-based matching

---

## Recommendations

- No dynamic values (timestamps, request IDs) in system prompt or tool definitions
- Load CLAUDE.md and skill instructions in consistent order
- Fixed tool set per session; no mid-conversation MCP server changes
- Static content before dynamic content in prompt structure
- Timestamps/session IDs as late as possible (user message, not system prompt)
- Use `/cost` to track per-request token usage and identify cache degradation
- Prefer CLI tools (`gh`, `aws`) over MCP servers when equivalent -- avoids persistent tool definition overhead

---

## Fork Session Pattern

Parallel sessions sharing the same base context cache via `--fork-session`.

| Approach | Token Multiplier | Use When |
|---|---|---|
| Fork session | 1.55x base context | Independent subtasks sharing same project context |
| Separate sessions | 3.75x base context | Unrelated tasks with no shared context |

Forked sessions inherit the parent's cache prefix — shared context reads at 0.1x token rate.

---

## Cache Breakeven Formula

Breakeven after just **2 requests** (5-min TTL: 1.25x write, 0.1x read):

```
Request 1: 1.25x (write) = 1.25x total
Request 2: 0.1x (read)   = 1.35x total for 2 requests
No cache:  1.0x × 2       = 2.00x total for 2 requests
```

1-hour TTL (2x write multiplier) also breaks even at 2 requests.

---

## Cache Hit Rate Formula

`cache_hit_rate = cache_read / (cache_read + cache_write + uncached_input)`

| Hit Rate | Assessment | Action |
|---|---|---|
| >90% | Excellent | Cache structure is well-optimised |
| 70-90% | Good | Check for minor cache-busting patterns |
| <70% | Poor | Likely dynamic content in system prompt or tool churn |

Target 90%+ for interactive sessions.
