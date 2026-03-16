---
name: pdf-simplifier
description: >
  Convert a PDF into an interactive web reader with three reading modes
  (ELI5/Medium/Full), chapter navigation, and math rendering.
  Only activate when invoked directly via /pdf-simplifier.
user_invocable: true
arguments:
  - name: pdf_path
    description: Path to the source PDF file
    required: true
---

# PDF-to-Web-Reader Skill

Converts a PDF into a self-contained static web reader with three reading modes (ELI5, Medium, Full), sidebar navigation, KaTeX math rendering, and extracted images.

## Pipeline Overview

| Stage | What | Tool | Output |
|-------|------|------|--------|
| 1 | Extract text + fonts | `scripts/extract_text.py` | `.state/pages.json` |
| 2 | Extract images | `scripts/extract_images.py` | `images/` + `.state/images.json` |
| 3 | Detect structure | `scripts/detect_structure.py` | `.state/structure.json` |
| 4 | Build content shell | `scripts/build_content_shell.py` | `.state/content-shell.json` + `.state/sections/*.txt` |
| 5 | Generate content | Claude (subagents) | `.state/sections/*.json` |
| 6 | Assemble site | Copy template + merge | `content.json` + `index.html` + `styles.css` + `app.js` |

## Quick Start

### 1. Get Inputs

The PDF path is provided as the skill argument (`pdf_path`). Verify the file exists:

```bash
test -f "{pdf_path}" && echo "OK" || echo "NOT FOUND"
```

If the file doesn't exist, report the error and stop.

**Ask the user** where they want the output directory. Do not assume a default — wait for their answer.

Optionally, ask if they have a **manual structure file** (a structure.json) they'd like to use.

### 2. Check Dependencies

```bash
python3 -c "import fitz; print(fitz.version)" 2>/dev/null || echo "MISSING"
```

If pymupdf is missing, ask the user:
> pymupdf is required for PDF extraction. Install it with `pip install pymupdf`?

### 3. Check for Resumability

If the output directory already exists, check `.state/progress.json`:

```bash
cat {output}/.state/progress.json 2>/dev/null
```

If it exists, report what's already done and offer to resume or start fresh.

## Stage Execution

### Stage 1: Extract Text

```bash
python3 {skill_dir}/scripts/extract_text.py "{pdf_path}" "{output_dir}"
```

Read the output JSON to confirm page count and outline entries. Report to user:
> Extracted text from {N} pages. Found {M} outline/bookmark entries.

### Stage 2: Extract Images

```bash
python3 {skill_dir}/scripts/extract_images.py "{pdf_path}" "{output_dir}"
```

Report:
> Extracted {N} images.

### Stage 3: Detect Structure

If the user provided a manual structure file, copy it to `.state/structure.json` instead of running detection:

```bash
cp "{manual_structure_path}" "{output_dir}/.state/structure.json"
```

Otherwise, run detection:

```bash
python3 {skill_dir}/scripts/detect_structure.py "{output_dir}/.state/pages.json" "{output_dir}"
```

**USER INTERACTION POINT**: Display the detected structure and ask for confirmation:

> **Detected structure** (method: {method}):
>
> **Title**: {title}
>
> | Chapter | Sections | Pages |
> |---------|----------|-------|
> | {ch.title} | {len(ch.sections)} | {first_page}-{last_page} |
> | ... | ... | ... |
>
> Does this look correct? You can:
> 1. Proceed with this structure
> 2. Provide a manual structure file (see format with `/pdf-simplifier help structure`)
> 3. Ask me to adjust specific chapters/sections

If the user wants adjustments, read `references/manual-structure-format.md` for the schema and help them create one.

### Stage 4: Build Content Shell

```bash
python3 {skill_dir}/scripts/build_content_shell.py "{output_dir}"
```

Report:
> Built content shell: {N} chapters, {M} sections. Math detected: {yes/no}.

### Stage 5: Generate Content

This is the core stage where Claude generates the three reading modes.

**USER INTERACTION POINT**: Before starting, report:
> Ready to generate content for {N} sections. This will use subagents to process sections in parallel. Proceed?

#### Content Generation Loop

1. Read `.state/progress.json` to find which sections are already complete
2. Read `.state/content-shell.json` to get the full section list
3. For each incomplete section, dispatch a subagent

**Subagent dispatch** - process 3-5 sections concurrently:

For each section, spawn an Agent with `subagent_type: "general-purpose"` and `model: "sonnet"`:

```
prompt: |
  You are generating content for a web reader. Read the reference files, then process this section.

  Read the content prompts reference:
  {skill_dir}/skills/pdf-simplifier/references/content-prompts.md

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
  {
    "id": "{section.id}",
    "title": "{section.title}",
    "full": "<p>HTML content...</p>",
    "medium": "<p>HTML content...</p>",
    "eli5": "<p>HTML content...</p>",
    "agentNotes": ["Note 1", "Note 2"]
  }

  IMPORTANT: Output ONLY the JSON file write. No other actions needed.
```

After each batch completes, update `.state/progress.json`:
```python
# Read current progress
progress = json.load(open(f"{output_dir}/.state/progress.json"))
progress["completedSections"].append(section_id)
progress["stage"] = "generating"
json.dump(progress, open(f"{output_dir}/.state/progress.json", "w"))
```

Report progress periodically:
> Generated {completed}/{total} sections...

### Stage 6: Assemble Site

Once all sections are generated:

1. **Copy template files** from `{skill_dir}/assets/template/` to `{output_dir}/`:
   ```bash
   cp {skill_dir}/skills/pdf-simplifier/assets/template/styles.css "{output_dir}/styles.css"
   cp {skill_dir}/skills/pdf-simplifier/assets/template/app.js "{output_dir}/app.js"
   ```

2. **Process index.html** - copy and replace `{{TITLE}}`:
   ```bash
   sed 's/{{TITLE}}/{escaped_title}/g' {skill_dir}/skills/pdf-simplifier/assets/template/index.html > "{output_dir}/index.html"
   ```

3. **Assemble content.json** - merge all section JSON files into the final content:

   Read `.state/content-shell.json` for the structure, then for each section read `.state/sections/{id}.json` and populate the fields. Write the final assembled JSON as `{output_dir}/content.json`.

   The content.json format:
   ```json
   {
     "meta": {
       "title": "Document Title",
       "hasMath": true
     },
     "chapters": [
       {
         "id": "ch1",
         "title": "Chapter Title",
         "sections": [
           {
             "id": "1.1",
             "title": "Section Title",
             "full": "<p>HTML...</p>",
             "medium": "<p>HTML...</p>",
             "eli5": "<p>HTML...</p>",
             "agentNotes": ["Note 1", "Note 2"],
             "images": ["fig-p5-1.png"]
           }
         ]
       }
     ]
   }
   ```

4. **Update progress**:
   ```python
   progress["stage"] = "complete"
   ```

5. **Report completion**:
   > Reader generated at `{output_dir}/`
   >
   > To view it:
   > ```bash
   > cd {output_dir} && python3 -m http.server 8000
   > ```
   > Then open http://localhost:8000

## Assembling content.json (Python snippet)

Use this to merge all section data into the final content.json:

```python
import json
from pathlib import Path

def assemble_content(output_dir):
    state = Path(output_dir) / ".state"

    with open(state / "content-shell.json") as f:
        shell = json.load(f)

    for chapter in shell["chapters"]:
        for section in chapter["sections"]:
            section_file = state / "sections" / f"{section['id']}.json"
            if section_file.exists():
                with open(section_file) as f:
                    data = json.load(f)
                section["full"] = data.get("full", section.get("full", ""))
                section["medium"] = data.get("medium", "")
                section["eli5"] = data.get("eli5", "")
                section["agentNotes"] = data.get("agentNotes", [])

    with open(Path(output_dir) / "content.json", "w") as f:
        json.dump(shell, f, ensure_ascii=False, indent=2)
```

Run this inline with the Bash tool after all sections are generated.

## Resumability

When invoked on an existing output directory:

1. Check `.state/progress.json`
2. If `stage` is `"complete"` → offer to regenerate specific sections or start fresh
3. If `stage` is `"generating"` → find incomplete sections and resume from there
4. If `stage` is `"content-shell-built"` → resume from Stage 5
5. If `.state/pages.json` exists but no `structure.json` → resume from Stage 3
6. If `.state/pages.json` exists and `structure.json` exists → resume from Stage 4

## Notes

- The `{skill_dir}` placeholder refers to the directory containing this SKILL.md file. Resolve it relative to the skill's location in the plugin.
- All Python scripts are self-contained and only require `pymupdf` (`pip install pymupdf`).
- The template files use KaTeX from CDN for math rendering - no local installation needed.
- For very large documents (100+ sections), consider increasing subagent parallelism to 5-8.
- If a subagent fails on a section, log the error and continue. The section can be retried by re-running the skill.
