# Skill Profile Report: {{skill_name}}

## Summary

- **Overall efficiency score**: {{overall_score}}/100
- **Estimated savings available**: {{total_token_savings}} tokens/session
- **Priority actions**: {{priority_action_count}}

## Structural Analysis

| Metric | Value | Target | Status |
|---|---|---|---|
| SKILL.md lines | {{body_lines}} | <500 | {{body_lines_status}} |
| Estimated tokens (L2) | {{body_estimated_tokens}} | <10,000 | {{body_tokens_status}} |
| Frontmatter tokens (L1) | {{frontmatter_tokens}} | <150 | {{frontmatter_tokens_status}} |
| Reference files (L3) | {{references_count}} | >0 if body >300 lines | {{references_status}} |
| Scripts | {{scripts_count}} | >0 if validations needed | {{scripts_status}} |
| Description quality | {{description_score}}/10 | >7 | {{description_status}} |

## Model Routing Audit

{{model_routing_section}}

## Context Pollution Scan

{{context_pollution_section}}

Cumulative savings over 20-turn session: ~{{cumulative_token_savings}} tokens

## Cache Hygiene Audit

{{cache_hygiene_section}}

## Delegation Patterns Audit

{{delegation_section}}

## Anti-Patterns Detected

{{anti_patterns_section}}

## Recommendations (ranked by impact)

| # | Action | Token Savings | Effort |
|---|---|---|---|---|
{{recommendations_table}}

## Agentic Review

{{agentic_review_section}}

## Generated Artefacts

{{generated_artefacts_section}}
