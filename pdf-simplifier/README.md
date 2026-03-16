# PDF-to-Web-Reader

A Claude Code skill that converts any PDF into an interactive, self-contained static web reader.

## Features

- **Three reading modes**: ELI5 (simple), Medium (intermediate), Full (faithful to source)
- **Chapter/section navigation** with sidebar
- **KaTeX math rendering** for technical documents
- **Image extraction** and placement
- **Resumable pipeline** - interrupt and resume without losing progress
- **Works on any PDF** - textbooks, papers, reports, manuals

## Installation

Install as a Claude Code plugin:

```bash
claude plugin add ~/dev/claude-tools/pdf-simplifier
```

## Dependencies

The extraction scripts require `pymupdf`:

```bash
pip install pymupdf
```

No other external dependencies. The web template uses KaTeX from CDN.

## Usage

In any Claude Code session:

```
/pdf-simplifier path/to/document.pdf
```

You'll be prompted for the output directory.

The skill runs a 6-stage pipeline:
1. Extract text with font metadata
2. Extract images
3. Detect document structure (chapters/sections)
4. Build content skeleton
5. Generate three reading modes per section (using Claude)
6. Assemble the static site

### Manual Structure

If automatic structure detection doesn't work well for your PDF, you can provide a manual structure file. See the skill's `references/manual-structure-format.md` for the schema.

### Resumability

If the process is interrupted, re-run `/pdf-simplifier` pointing at the same output directory. It will detect completed stages and resume where it left off.

## Output

The output directory is a self-contained static site. Serve it with any HTTP server:

```bash
cd reader/
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

## How It Works

The extraction pipeline (stages 1-4) uses Python scripts with `pymupdf` to pull text, images, and structure from the PDF. Content generation (stage 5) uses Claude itself - spawning parallel subagents to process sections concurrently. The final assembly (stage 6) combines everything into a static site using a pre-built HTML/CSS/JS template.
