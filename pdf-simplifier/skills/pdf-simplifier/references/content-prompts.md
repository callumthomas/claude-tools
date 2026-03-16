# Content Generation Prompts

These are the prompt templates used by the skill to generate the three reading modes. The skill reads raw section text and produces HTML content for each mode.

## Base Context (included in all prompts)

```
You are converting a section of a document into HTML content for a web reader. The reader supports three modes: Full, Medium, and ELI5.

Rules:
- Output clean, semantic HTML (p, ul, ol, strong, em, h3, h4 tags)
- Do NOT include the section title as a heading (the reader handles that)
- Preserve all factual content - never invent information not in the source
- For LaTeX math, use delimiters: $...$ for inline, $$...$$ for display
- Keep image references as-is (the reader handles image display separately)
```

## Full Mode Prompt

```
Generate the FULL mode content for this section. This should be a faithful, well-formatted HTML rendering of the source text.

Guidelines:
- Preserve all technical detail, formulas, and nuance from the source
- Improve formatting: add paragraph breaks, lists where appropriate, bold key terms
- Convert any mathematical notation to LaTeX delimiters ($...$ inline, $$...$$ display)
- Fix OCR artifacts or extraction noise (broken words, stray characters)
- Maintain the original structure and flow of ideas
- Do NOT add information not present in the source
- Do NOT summarize or simplify - this is the full-fidelity mode

Source text:
---
{raw_text}
---

Output only the HTML content, no wrapping tags or explanation.
```

## Medium Mode Prompt

```
Generate the MEDIUM mode content for this section. This is a condensed version for readers who want key concepts without every detail.

Guidelines:
- Cover all major concepts and key points
- Reduce to roughly 40-60% of the full content length
- Simplify complex sentences but keep technical accuracy
- Keep important formulas and definitions, skip derivations
- Use bullet points for lists of related items
- Bold key terms and concepts on first mention
- Accessible to someone with basic domain knowledge

Source text:
---
{raw_text}
---

Output only the HTML content, no wrapping tags or explanation.
```

## ELI5 Mode Prompt

```
Generate the ELI5 mode content for this section. Explain the core ideas as if to a curious, intelligent person with no background in this field.

Guidelines:
- Use plain language, everyday analogies, and concrete examples
- Reduce to roughly 20-30% of the full content length
- Skip formulas entirely unless they're central to understanding (then explain in words)
- Focus on intuition and "why this matters" over technical details
- Use short paragraphs and conversational tone
- Bold key terms and briefly define them in parentheses when first used
- It's OK to say "the details are in Full mode" for complex topics

Source text:
---
{raw_text}
---

Output only the HTML content, no wrapping tags or explanation.
```

## Agent Notes Prompt

```
Generate 2-4 brief "agent notes" for this section. These are additional insights that add value beyond the source text.

Good agent notes:
- Connect this topic to modern developments or practical applications
- Clarify common misconceptions
- Highlight why something is important or counter-intuitive
- Provide helpful context that aids understanding

Bad agent notes:
- Simply restating what the text says
- Generic observations ("this is an important topic")
- Speculative claims

Source text:
---
{raw_text}
---

Output a JSON array of strings, each string being one note (plain text, no HTML).
Example: ["Note one here.", "Note two here."]
```

## Technical/Math-Heavy Variant

When `meta.hasMath` is true, append to all content prompts:

```
This document is math-heavy. Pay special attention to:
- Converting all mathematical expressions to proper LaTeX
- Using $...$ for inline math and $$...$$ for display math
- Preserving variable names, subscripts, superscripts exactly
- Using \text{} for words within math expressions
- Common patterns: vectors as \mathbf{x}, matrices as \mathbf{X}, sets as \mathcal{S}
```

## Code-Heavy Variant

When code blocks are detected in the source text, append:

```
This section contains code. Preserve code blocks using <pre><code class="language-{lang}">...</code></pre> tags. Keep code exactly as-is - do not modify variable names, formatting, or logic.
```
