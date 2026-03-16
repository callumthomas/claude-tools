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
| 6 | Assemble site | `scripts/validate_sections.py` + `scripts/assemble_content.py` + `scripts/render_template.py` | `content.json` + `index.html` + `styles.css` + `app.js` |

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

For each section, spawn an Agent with `subagent_type: "general-purpose"` and `model: "sonnet"`.

Read the prompt template from `references/subagent-prompt.md` and fill in the variables:
- `{skill_dir}` — path to this skill's directory
- `{section.id}`, `{section.title}`, `{section.startPage}`, `{section.endPage}` — from the content shell
- `{hasMath}` — from `.state/content-shell.json` meta
- `{output_dir}` — the user's chosen output directory

After each batch of subagents completes, update `.state/progress.json` yourself (do not have subagents write to this file — concurrent writes will corrupt it):

```bash
python3 -c "
import json
p = json.load(open('{output_dir}/.state/progress.json'))
p['completedSections'].extend([{list of completed section IDs from this batch}])
p['stage'] = 'generating'
json.dump(p, open('{output_dir}/.state/progress.json', 'w'))
"
```

Report progress periodically:
> Generated {completed}/{total} sections...

### Stage 6: Assemble Site

Once all sections are generated:

1. **Validate sections:**
   ```bash
   python3 {skill_dir}/scripts/validate_sections.py "{output_dir}"
   ```
   If errors are reported, log them. Retry failed sections or proceed with what's available.

2. **Assemble content.json:**
   ```bash
   python3 {skill_dir}/scripts/assemble_content.py "{output_dir}"
   ```

3. **Render template:**
   Read `.state/content-shell.json` to get the title and `meta.hasMath` flag, then:
   ```bash
   python3 {skill_dir}/scripts/render_template.py \
     "{skill_dir}/assets/template" \
     "{output_dir}" \
     "{title}" \
     "{has_math}"
   ```
   This copies template files, safely substitutes the title, and bundles KaTeX locally when math is detected (falls back to CDN if download fails).

4. **Update progress:**
   ```bash
   python3 -c "
   import json
   p = json.load(open('{output_dir}/.state/progress.json'))
   p['stage'] = 'complete'
   json.dump(p, open('{output_dir}/.state/progress.json', 'w'))
   "
   ```

5. **Report completion:**
   > Reader generated at `{output_dir}/`
   >
   > To view it:
   > ```bash
   > cd {output_dir} && python3 -m http.server 8000
   > ```
   > Then open http://localhost:8000

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
- KaTeX is bundled locally into the output when math is detected, making the reader work offline. Falls back to CDN if the download fails.
- For very large documents (100+ sections), consider increasing subagent parallelism to 5-8.
- If a subagent fails on a section, log the error and continue. The section can be retried by re-running the skill.
