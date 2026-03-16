# Manual Structure File Format

When automatic structure detection doesn't work well, users can provide a manual structure file. The skill will use this instead of running `detect_structure.py`.

## File Format

JSON file with this schema:

```json
{
  "title": "Document Title",
  "chapters": [
    {
      "id": "ch1",
      "title": "Chapter Title",
      "sections": [
        {
          "id": "1.1",
          "title": "Section Title",
          "startPage": 1,
          "endPage": 10
        },
        {
          "id": "1.2",
          "title": "Another Section",
          "startPage": 11,
          "endPage": 20
        }
      ]
    },
    {
      "id": "ch2",
      "title": "Second Chapter",
      "sections": [
        {
          "id": "2.1",
          "title": "First Section of Ch2",
          "startPage": 21,
          "endPage": 35
        }
      ]
    }
  ]
}
```

## Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Document title displayed in the header |
| `chapters` | array | yes | Top-level groupings (at least one) |
| `chapters[].id` | string | yes | Unique chapter ID (e.g. `ch1`, `ch2`) |
| `chapters[].title` | string | yes | Chapter title shown in sidebar |
| `chapters[].sections` | array | yes | Sections within the chapter (at least one) |
| `sections[].id` | string | yes | Unique section ID (e.g. `1.1`, `intro`) |
| `sections[].title` | string | yes | Section title shown in sidebar and content |
| `sections[].startPage` | int | yes | First page of this section (1-indexed) |
| `sections[].endPage` | int | yes | Last page of this section (inclusive) |

## Rules

- Page numbers are 1-indexed (first page of the PDF is page 1)
- `endPage` is inclusive (a section spanning pages 1-10 includes page 10)
- Every page in the PDF should be covered by exactly one section
- Section IDs must be unique across the entire document
- Sections within a chapter should be in page order
- Chapters should be in page order
- IDs can be any string but numeric-prefixed IDs (like `1.1`, `2.3`) get displayed as `1.1 Section Title` in the sidebar

## Quick Start

The easiest way to create a manual structure file:

1. Open the PDF and note down the chapter/section structure from the table of contents
2. For each section, note the start page
3. End pages are automatically the page before the next section starts (but you still need to specify them)
4. Save as `structure.json` in the output directory

## Example: Simple Document

For a 50-page report with three sections:

```json
{
  "title": "Quarterly Report Q4 2025",
  "chapters": [
    {
      "id": "ch1",
      "title": "Report",
      "sections": [
        { "id": "exec", "title": "Executive Summary", "startPage": 1, "endPage": 5 },
        { "id": "findings", "title": "Key Findings", "startPage": 6, "endPage": 30 },
        { "id": "appendix", "title": "Appendix", "startPage": 31, "endPage": 50 }
      ]
    }
  ]
}
```
