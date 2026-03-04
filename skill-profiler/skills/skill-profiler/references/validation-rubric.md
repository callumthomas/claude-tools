# Validation Rubric

After each analysis step, the agent validates script findings against the actual files. This rubric defines what to check.

**Step mapping:**
- Sections 2, 3, 5 → Step 2 (Static Analysis)
- Section 4 → Step 3 (Model Routing Audit)
- Section 1 → Step 4 (Context Pollution Scan)

## 1. Context Pollution Review

Read the SKILL.md body and identify operations that generate large context but could be delegated, beyond what the regex scanner catches.

**Flag when:**
- Instructions imply sequential reads without parallelisation (e.g. "read each file and summarise" across >3 files)
- Tool calls whose output would be large but isn't summarised before use
- Multi-step processing chains where intermediate results inflate context
- Expected output exceeds 1,500 tokens (the break-even threshold for delegation)

**Ignore when:**
- Sequential reads are genuinely needed (each read depends on prior output)
- The operation is the skill's core purpose (e.g. a code review skill reading files)
- Output is already bounded by explicit limits in the instructions

## 2. Description Effectiveness

Assess whether the description would actually route correctly for the intended use cases.

**Flag when:**
- Trigger phrases don't match natural user phrasing (too technical, too generic)
- Negative triggers are missing for common false-activation scenarios
- If `--others` descriptions were provided: semantic collision exists even though keyword overlap is below the 60% static threshold (e.g. "review code quality" vs "audit code standards")

**Ignore when:**
- Keyword overlap is high but semantic intent is clearly different
- The skill targets a niche domain where precise phrasing is expected

## 3. Anti-Pattern Contextual Review

For each anti-pattern flagged by the static analysis, assess whether it's genuinely problematic in context.

**Flag as false positive when:**
- "prompt-as-enforcement" (e.g. "always confirm before deleting") is a compliance or safety requirement
- Inline troubleshooting >30 lines where troubleshooting *is* the skill's primary purpose
- Progressive disclosure violation where the content is genuinely needed on every invocation

**Flag as false negative when:**
- Implicit iteration without maxTurns (static scanner doesn't detect loop risk from natural language)
- Unrestricted tool scope that could be narrowed (e.g. full Bash access when only Read/Grep is needed)
- Duplicate instructions across SKILL.md and referenced files

## 4. Model Routing Validation

For each agent file, read its actual instructions and assess whether the statically-recommended model tier matches the cognitive complexity.

**Flag when:**
- Tool presence is misleading: Bash used only for simple commands (e.g. `grep`, `ls`) → Haiku is fine despite static scanner recommending Sonnet
- Task requires reasoning beyond what tool classification suggests: Read-only tools but task involves architectural analysis → Sonnet/Opus needed
- Model is set to `inherit` but the parent context uses a higher tier than the task requires

**Ignore when:**
- Static recommendation aligns with actual task complexity
- The agent has no model field and inherits appropriately

## 5. Instruction Coherence

Check for ambiguous, contradictory, or missing instructions in the SKILL.md body.

**Flag when:**
- Two instructions contradict (e.g. "always use subagents" + "never spawn subagents for simple tasks" without a clear boundary)
- Missing error handling instructions for likely failure modes
- Instructions that could cause the agent to loop (e.g. "retry until successful" without a limit)
- Implicit assumptions about environment or state that aren't validated

**Ignore when:**
- Apparent contradictions have clear conditional resolution in context
- The skill targets experienced users who understand implicit conventions

## Output Format

Present findings as a numbered list matching the format used in the Anti-Patterns section:

```
1. **[SEVERITY]** Finding category - Description of the issue -> Recommended fix
```

Severity levels:
- **HIGH**: Causes incorrect behaviour, significant token waste, or routing failures
- **MEDIUM**: Suboptimal but functional; worth fixing for efficiency
- **LOW**: Minor improvement; fix if convenient

Group findings by rubric area (Context Pollution, Description Effectiveness, Anti-Pattern Review, Model Routing, Instruction Coherence). If a rubric area has no findings, omit it.
