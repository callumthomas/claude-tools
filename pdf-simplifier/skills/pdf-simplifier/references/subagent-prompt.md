# Content Generation Subagent Prompt

Use this prompt template when dispatching subagents for Stage 5. Replace all `{variables}` with actual values.

---

You are generating content for a web reader. Read the reference files, then process this section.

Read the content prompts reference:
{skill_dir}/references/content-prompts.md

Section details:
- ID: {section.id}
- Title: {section.title}
- Pages: {section.startPage}-{section.endPage}
- Document has math: {hasMath}

Read the raw section text:
{output_dir}/.state/sections/{section.id}.txt

Generate four outputs using the prompts from content-prompts.md:
1. `full` - Faithful HTML rendering (use Full Mode Prompt)
2. `medium` - Condensed version (use Medium Mode Prompt)
3. `eli5` - Simple explanation (use ELI5 Mode Prompt)
4. `agentNotes` - 2-4 insight notes (use Agent Notes Prompt, output as JSON array)

If the document has math, apply the Technical/Math-Heavy Variant additions.
If the source text contains code blocks, apply the Code-Heavy Variant additions.

Write the result as JSON to: {output_dir}/.state/sections/{section.id}.json

The JSON format:
```json
{
  "id": "{section.id}",
  "title": "{section.title}",
  "full": "<p>HTML content...</p>",
  "medium": "<p>HTML content...</p>",
  "eli5": "<p>HTML content...</p>",
  "agentNotes": ["Note 1", "Note 2"]
}
```

Output ONLY the JSON file write. No other actions needed.
