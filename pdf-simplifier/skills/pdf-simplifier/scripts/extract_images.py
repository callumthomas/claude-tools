#!/usr/bin/env python3
"""Extract images from a PDF with page mapping."""

import json
import sys
from pathlib import Path

import fitz

MIN_DIMENSION = 50
MIN_AREA = 5000


def extract_images(pdf_path: str, output_dir: str) -> list:
    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    state_dir = Path(output_dir) / ".state"
    state_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    seen_digests = set()
    image_records = []
    fig_counter = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)

        for img_info in image_list:
            xref = img_info[0]
            width = img_info[2]
            height = img_info[3]

            if width < MIN_DIMENSION or height < MIN_DIMENSION:
                continue
            if width * height < MIN_AREA:
                continue

            try:
                pix = fitz.Pixmap(doc, xref)
            except Exception:
                continue

            digest = hash(pix.samples)
            if digest in seen_digests:
                continue
            seen_digests.add(digest)

            if pix.alpha:
                pix = fitz.Pixmap(fitz.csRGB, pix)

            if pix.n > 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)

            fig_counter += 1
            filename = f"fig-p{page_num + 1}-{fig_counter}.png"
            filepath = images_dir / filename
            pix.save(str(filepath))

            image_records.append({
                "filename": filename,
                "page": page_num + 1,
                "width": width,
                "height": height,
            })

    doc.close()

    output_path = state_dir / "images.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(image_records, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "ok",
        "imageCount": len(image_records),
        "outputPath": str(output_path),
    }))
    return image_records


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <pdf_path> <output_dir>", file=sys.stderr)
        sys.exit(1)
    extract_images(sys.argv[1], sys.argv[2])
