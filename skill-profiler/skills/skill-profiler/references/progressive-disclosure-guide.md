# Progressive Disclosure Guide

---

## Key Principle

**Files don't consume context until accessed.**

---

## Three-Tier Loading System

### Level 1: YAML Frontmatter (Always Loaded)

- **What**: The `name` and `description` fields from SKILL.md frontmatter
- **When loaded**: Always present in the system prompt for every enabled skill
- **Token budget**: ~50-150 tokens per skill
- **Purpose**: Gives Claude enough information to decide whether to load the skill for the current task

Every enabled skill contributes L1 to every request (~100 tokens saved per disabled skill).

### Level 2: SKILL.md Body (Loaded on Match)

- **What**: The full body of SKILL.md after the frontmatter
- **When loaded**: When Claude determines the skill is relevant to the current user request
- **Token budget**: Target <500 lines, <10,000 tokens
- **Purpose**: Contains the core workflow instructions, decision logic, and quick-reference material needed to execute the skill

L2 should be self-contained for the common case.

### Level 3: Linked Files (Loaded on Demand)

- **What**: Files in references/, scripts/, assets/, and any other linked files
- **When loaded**: Only when Claude navigates to them during execution (e.g., reads a referenced file, runs a script)
- **Token budget**: No hard limit, but each file should be focused and purposeful
- **Purpose**: Detailed reference material, examples, templates, troubleshooting guides, and executable scripts

L3 files consume zero context tokens until accessed.

---

## Token Budget Summary

| Tier | Content | Budget | Loaded When |
|---|---|---|---|
| L1 | Frontmatter (name + description) | 50-150 tokens | Every request (all enabled skills) |
| L2 | SKILL.md body | <10,000 tokens | Skill matches user request |
| L3 | references/, scripts/, assets/ | Unlimited (on-demand) | Agent reads file during execution |

---

## Example Optimised Skill Structure

```
skill-name/
  SKILL.md           (420 lines, ~8,400 tokens -- workflows + quick ref)
  REFERENCE.md       (350 lines, loaded on-demand)
  EXAMPLES.md        (180 lines, loaded on-demand)
  PATTERNS.md        (200 lines, loaded on-demand)
  TROUBLESHOOTING.md (100 lines, loaded on-demand)
  scripts/
    validate.sh      (code never enters context until executed)
    setup.sh
```

L1: ~100 tokens (every request) | L2: ~8,400 tokens (on trigger) | L3: 0 until needed

---

## Guidelines: What Goes Where

### L2 (SKILL.md body) -- Keep Here

- Core workflow steps (the main execution path)
- Decision logic and branching rules
- Quick-reference tables needed during every execution
- Output format specifications
- Critical constraints and guardrails

### L3 (Linked files) -- Move Here

- Detailed technique catalogs and reference tables
- Extended examples beyond minimal working demonstrations
- Troubleshooting guides and edge-case handling
- Background theory and rationale
- Template files and boilerplate
- Rarely-needed decision matrices
- Historical context or changelog information

### Rule of Thumb

\>80% of executions → L2. <50% → L3. In between → brief L2 summary with link to L3.
