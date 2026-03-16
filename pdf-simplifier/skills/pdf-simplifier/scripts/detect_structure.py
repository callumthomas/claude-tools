#!/usr/bin/env python3
"""Detect chapter/section structure from extracted PDF text."""

import json
import re
import sys
from collections import Counter
from pathlib import Path


def detect_from_outline(outline: list, page_count: int) -> dict | None:
    if not outline:
        return None

    chapters = []
    current_chapter = None
    current_sections = []

    for i, entry in enumerate(outline):
        next_page = outline[i + 1]["page"] if i + 1 < len(outline) else page_count + 1

        if entry["level"] == 1:
            if current_chapter is not None:
                chapters.append({
                    "id": f"ch{len(chapters) + 1}",
                    "title": current_chapter["title"],
                    "sections": current_sections,
                })
            current_chapter = entry
            current_sections = []

            if not any(e["level"] == 2 and outline.index(e) > i for e in outline[i+1:i+50]):
                current_sections.append({
                    "id": f"{len(chapters) + 1}.1",
                    "title": entry["title"],
                    "startPage": entry["page"],
                    "endPage": next_page - 1,
                })
        elif entry["level"] == 2 and current_chapter is not None:
            current_sections.append({
                "id": f"{len(chapters) + 1}.{len(current_sections) + 1}",
                "title": entry["title"],
                "startPage": entry["page"],
                "endPage": next_page - 1,
            })

    if current_chapter is not None:
        chapters.append({
            "id": f"ch{len(chapters) + 1}",
            "title": current_chapter["title"],
            "sections": current_sections,
        })

    if not chapters:
        return None

    for ch in chapters:
        if not ch["sections"]:
            ch["sections"].append({
                "id": f"{ch['id'].replace('ch', '')}.1",
                "title": ch["title"],
                "startPage": 1,
                "endPage": page_count,
            })

    fix_end_pages(chapters, page_count)
    return {"chapters": chapters}


def detect_from_fonts(pages: list) -> dict | None:
    size_char_count = Counter()
    for page in pages:
        for block in page.get("text_blocks", []):
            size_char_count[block["size"]] += len(block["text"])

    if len(size_char_count) < 2:
        return None

    body_size = size_char_count.most_common(1)[0][0]
    heading_sizes = sorted(
        [s for s in size_char_count if s > body_size + 1], reverse=True
    )

    if not heading_sizes:
        return None

    chapter_size = heading_sizes[0]
    section_size = heading_sizes[1] if len(heading_sizes) > 1 else None

    chapters = []
    current_chapter = None
    current_sections = []

    for page in pages:
        page_num = page["page"]
        for block in page.get("text_blocks", []):
            text = block["text"]
            size = block["size"]

            if len(text) > 100:
                continue

            if abs(size - chapter_size) < 0.5:
                if current_chapter is not None:
                    if not current_sections:
                        current_sections.append({
                            "id": f"{len(chapters) + 1}.1",
                            "title": current_chapter["title"],
                            "startPage": current_chapter["page"],
                            "endPage": page_num - 1,
                        })
                    chapters.append({
                        "id": f"ch{len(chapters) + 1}",
                        "title": current_chapter["title"],
                        "sections": current_sections,
                    })
                current_chapter = {"title": text, "page": page_num}
                current_sections = []

            elif (
                section_size
                and abs(size - section_size) < 0.5
                and current_chapter is not None
            ):
                current_sections.append({
                    "id": f"{len(chapters) + 1}.{len(current_sections) + 1}",
                    "title": text,
                    "startPage": page_num,
                    "endPage": page_num,
                })

    if current_chapter is not None:
        if not current_sections:
            current_sections.append({
                "id": f"{len(chapters) + 1}.1",
                "title": current_chapter["title"],
                "startPage": current_chapter["page"],
                "endPage": len(pages),
            })
        chapters.append({
            "id": f"ch{len(chapters) + 1}",
            "title": current_chapter["title"],
            "sections": current_sections,
        })

    if len(chapters) < 2:
        return None

    fix_end_pages(chapters, len(pages))
    return {"chapters": chapters}


def detect_from_patterns(pages: list) -> dict | None:
    chapter_pattern = re.compile(
        r"^(?:Chapter|CHAPTER|Part|PART)\s+(\d+)[.:)?\s]+(.+)$", re.MULTILINE
    )
    section_pattern = re.compile(
        r"^(\d+)\.(\d+)\s+(.+)$", re.MULTILINE
    )

    chapters = []
    current_chapter = None
    current_sections = []

    for page in pages:
        page_num = page["page"]
        text = page["text"]

        for match in chapter_pattern.finditer(text):
            ch_num = match.group(1)
            ch_title = match.group(2).strip()

            if current_chapter is not None:
                if not current_sections:
                    current_sections.append({
                        "id": f"{current_chapter['num']}.1",
                        "title": current_chapter["title"],
                        "startPage": current_chapter["page"],
                        "endPage": page_num - 1,
                    })
                chapters.append({
                    "id": f"ch{current_chapter['num']}",
                    "title": current_chapter["title"],
                    "sections": current_sections,
                })

            current_chapter = {"num": ch_num, "title": ch_title, "page": page_num}
            current_sections = []

        if current_chapter is not None:
            for match in section_pattern.finditer(text):
                sec_ch = match.group(1)
                sec_num = match.group(2)
                sec_title = match.group(3).strip()
                if sec_ch == current_chapter["num"]:
                    current_sections.append({
                        "id": f"{sec_ch}.{sec_num}",
                        "title": sec_title,
                        "startPage": page_num,
                        "endPage": page_num,
                    })

    if current_chapter is not None:
        if not current_sections:
            current_sections.append({
                "id": f"{current_chapter['num']}.1",
                "title": current_chapter["title"],
                "startPage": current_chapter["page"],
                "endPage": len(pages),
            })
        chapters.append({
            "id": f"ch{current_chapter['num']}",
            "title": current_chapter["title"],
            "sections": current_sections,
        })

    if not chapters:
        return None

    fix_end_pages(chapters, len(pages))
    return {"chapters": chapters}


def detect_fallback(pages: list, pages_per_section: int = 10) -> dict:
    sections = []
    for i in range(0, len(pages), pages_per_section):
        start = i + 1
        end = min(i + pages_per_section, len(pages))
        sections.append({
            "id": f"1.{len(sections) + 1}",
            "title": f"Pages {start}-{end}",
            "startPage": start,
            "endPage": end,
        })

    return {
        "chapters": [{
            "id": "ch1",
            "title": "Document",
            "sections": sections,
        }]
    }


def fix_end_pages(chapters: list, total_pages: int):
    all_sections = []
    for ch in chapters:
        all_sections.extend(ch["sections"])

    for i, section in enumerate(all_sections):
        if i + 1 < len(all_sections):
            next_start = all_sections[i + 1]["startPage"]
            if section["endPage"] < next_start - 1 or section["endPage"] == section["startPage"]:
                section["endPage"] = next_start - 1

    if all_sections:
        all_sections[-1]["endPage"] = total_pages


def detect_title(pages: list, outline: list) -> str:
    if outline:
        for entry in outline:
            if entry["level"] == 0:
                return entry["title"]

    if pages:
        first_page = pages[0]
        candidates = [
            b for b in first_page.get("text_blocks", [])
            if 3 < len(b["text"]) < 200
        ]
        if candidates:
            largest = max(candidates, key=lambda b: b["size"])
            return largest["text"]

    return "Untitled Document"


def detect_structure(pages_json_path: str, output_dir: str) -> dict:
    state_dir = Path(output_dir) / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)

    with open(pages_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pages = data["pages"]
    outline = data.get("outline", [])
    page_count = data.get("pageCount", len(pages))

    title = detect_title(pages, outline)

    result = detect_from_outline(outline, page_count)
    method = "outline"

    if result is None:
        result = detect_from_patterns(pages)
        method = "patterns"

    if result is None:
        result = detect_from_fonts(pages)
        method = "fonts"

    if result is None:
        result = detect_fallback(pages)
        method = "fallback"

    structure = {
        "title": title,
        "detectionMethod": method,
        "chapters": result["chapters"],
    }

    output_path = state_dir / "structure.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    total_sections = sum(len(ch["sections"]) for ch in structure["chapters"])
    print(json.dumps({
        "status": "ok",
        "title": title,
        "method": method,
        "chapters": len(structure["chapters"]),
        "sections": total_sections,
        "outputPath": str(output_path),
    }))
    return structure


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <pages_json_path> <output_dir>", file=sys.stderr)
        sys.exit(1)
    detect_structure(sys.argv[1], sys.argv[2])
