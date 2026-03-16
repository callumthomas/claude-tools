#!/usr/bin/env python3
"""Extract text and font metadata from a PDF, page by page."""

import json
import sys
from pathlib import Path

import fitz


def extract_text(pdf_path: str, output_dir: str) -> dict:
    state_dir = Path(output_dir) / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)

    outline = []
    toc = doc.get_toc(simple=True)
    for level, title, page_num in toc:
        outline.append({"level": level, "title": title, "page": page_num})

    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        fonts = {}
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    font_key = f"{span['font']}_{span['size']:.1f}_{span['flags']}"
                    if font_key not in fonts:
                        fonts[font_key] = {
                            "name": span["font"],
                            "size": round(span["size"], 1),
                            "flags": span["flags"],
                            "count": 0,
                        }
                    fonts[font_key]["count"] += len(span["text"].strip())

        pages.append({
            "page": page_num + 1,
            "text": text,
            "fonts": list(fonts.values()),
        })

    doc.close()

    result = {"pages": pages, "outline": outline, "pageCount": len(pages)}

    output_path = state_dir / "pages.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "ok",
        "pageCount": len(pages),
        "outlineEntries": len(outline),
        "outputPath": str(output_path),
    }))
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <pdf_path> <output_dir>", file=sys.stderr)
        sys.exit(1)
    extract_text(sys.argv[1], sys.argv[2])
