# Structure Detection Guide

The `detect_structure.py` script uses a cascade of detection methods. This document explains each and when to intervene.

## Detection Cascade

### 1. PDF Outline/Bookmarks (most reliable)

Many PDFs embed a table of contents as "bookmarks" (also called the outline). When present, this is the most reliable source. The script reads level-1 entries as chapters and level-2 entries as sections.

**When it works well**: Published books, official reports, well-authored academic papers.

**When it fails**: Scanned PDFs, PDFs generated from web pages, documents where bookmarks don't match actual content structure.

### 2. Numbered Heading Patterns

Regex-based detection of common heading formats:
- `Chapter N: Title` / `CHAPTER N Title`
- `Part N: Title`
- `N.N Title` (section numbering like 1.1, 2.3)

**When it works well**: Textbooks, technical manuals, standards documents.

**When it fails**: Documents without numbered headings, creative/literary works.

### 3. Font-Size Heuristic

Analyzes font metadata to identify heading hierarchy:
- Largest font size (above body text) → chapter headings
- Second-largest → section headings

**When it works well**: Documents with consistent formatting.

**When it fails**: Documents with decorative fonts, variable formatting, or where font metadata is unreliable.

### 4. Fallback (every N pages)

When no structural signals are found, the document is split into sections of approximately 10 pages each. This ensures the reader is still usable, but the structure won't reflect actual content divisions.

## When to Use Manual Structure

If the detected structure is wrong, the user should provide a manual structure file. Common cases:

- PDF has no bookmarks and uses non-standard heading formats
- The document is a scan with inconsistent OCR
- The document mixes multiple structural conventions
- Sections should be split differently than the automatic detection suggests

See `manual-structure-format.md` for the schema.

## Reviewing Detection Results

After structure detection, the skill displays:
- Detection method used
- Number of chapters and sections found
- Chapter/section titles

The user should confirm this looks correct before proceeding to content generation. Key things to check:

1. **Chapter count** - Does it match the actual document?
2. **Section titles** - Are they real headings or garbage text?
3. **Page ranges** - Do sections cover reasonable page spans?
4. **Missing content** - Are there pages not covered by any section?
