#!/usr/bin/env python3
"""Build content shell from structure, text, and images."""

import json
import sys
from pathlib import Path


def build_content_shell(output_dir: str) -> dict:
    state_dir = Path(output_dir) / ".state"
    sections_dir = state_dir / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)

    with open(state_dir / "structure.json", "r", encoding="utf-8") as f:
        structure = json.load(f)

    with open(state_dir / "pages.json", "r", encoding="utf-8") as f:
        pages_data = json.load(f)

    images_path = state_dir / "images.json"
    images = []
    if images_path.exists():
        with open(images_path, "r", encoding="utf-8") as f:
            images = json.load(f)

    page_text = {}
    for page in pages_data["pages"]:
        page_text[page["page"]] = page["text"]

    page_images = {}
    for img in images:
        pg = img["page"]
        if pg not in page_images:
            page_images[pg] = []
        page_images[pg].append(img["filename"])

    chapters = []
    for ch in structure["chapters"]:
        sections = []
        for section in ch["sections"]:
            start = section["startPage"]
            end = section["endPage"]

            text_parts = []
            section_images = []
            for pg in range(start, end + 1):
                if pg in page_text:
                    text_parts.append(page_text[pg])
                if pg in page_images:
                    section_images.extend(page_images[pg])

            raw_text = "\n\n".join(text_parts)

            section_file = sections_dir / f"{section['id']}.txt"
            with open(section_file, "w", encoding="utf-8") as f:
                f.write(raw_text)

            sections.append({
                "id": section["id"],
                "title": section["title"],
                "startPage": start,
                "endPage": end,
                "full": "",
                "medium": "",
                "eli5": "",
                "agentNotes": [],
                "images": section_images,
            })

        chapters.append({
            "id": ch["id"],
            "title": ch["title"],
            "sections": sections,
        })

    has_math = any(
        delim in page.get("text", "")
        for page in pages_data["pages"]
        for delim in ["\\(", "\\[", "$$", "$"]
    )

    content_shell = {
        "meta": {
            "title": structure["title"],
            "hasMath": has_math,
            "generatedSections": [],
        },
        "chapters": chapters,
    }

    output_path = state_dir / "content-shell.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(content_shell, f, ensure_ascii=False, indent=2)

    progress = {
        "totalSections": sum(len(ch["sections"]) for ch in chapters),
        "completedSections": [],
        "stage": "content-shell-built",
    }
    with open(state_dir / "progress.json", "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

    total_sections = progress["totalSections"]
    section_files = list(sections_dir.glob("*.txt"))
    print(json.dumps({
        "status": "ok",
        "chapters": len(chapters),
        "sections": total_sections,
        "sectionFiles": len(section_files),
        "hasMath": has_math,
        "outputPath": str(output_path),
    }))
    return content_shell


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output_dir>", file=sys.stderr)
        sys.exit(1)
    build_content_shell(sys.argv[1])
