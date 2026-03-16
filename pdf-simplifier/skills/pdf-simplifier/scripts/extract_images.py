#!/usr/bin/env python3
"""Extract images from a PDF using three strategies:
1. Caption-based figure detection (renders the region above figure captions)
2. Drawing cluster detection (finds dense vector graphic regions)
3. Embedded raster extraction (the original get_images approach)
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

MIN_DIMENSION = 50
MIN_AREA = 5000
RENDER_DPI = 200
MIN_DRAWING_COMMANDS = 15
CLUSTER_GAP = 30
CAPTION_PATTERN = re.compile(
    r"^(Fig(?:ure)?|Chart|Diagram|Table|Exhibit)\s*\.?\s*\d+",
    re.IGNORECASE | re.MULTILINE,
)
REGION_PAD = 10


def _pixel_digest(pix):
    return hashlib.sha256(pix.samples).hexdigest()


def _save_image(pix, images_dir, page_num, fig_counter, seen_digests, source):
    digest = _pixel_digest(pix)
    if digest in seen_digests:
        return None
    seen_digests.add(digest)

    if pix.alpha:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    if pix.n > 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    filename = f"fig-p{page_num + 1}-{fig_counter}.png"
    pix.save(str(images_dir / filename))

    return {
        "filename": filename,
        "page": page_num + 1,
        "width": pix.width,
        "height": pix.height,
        "source": source,
    }


def _overlaps_any(rect, existing_rects, threshold=0.5):
    for er in existing_rects:
        intersection = rect & er
        if intersection.is_empty:
            continue
        overlap_area = intersection.width * intersection.height
        rect_area = rect.width * rect.height
        if rect_area > 0 and overlap_area / rect_area > threshold:
            return True
    return False


def _find_caption_figures(page, page_num, images_dir, fig_counter, seen_digests):
    records = []
    clip_rects = []
    text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    page_rect = page.rect

    caption_blocks = []
    for block in text_dict["blocks"]:
        if block["type"] != 0:
            continue
        block_text = ""
        for line in block["lines"]:
            block_text += "".join(span["text"] for span in line["spans"])
        if CAPTION_PATTERN.search(block_text.strip()):
            caption_blocks.append(block["bbox"])

    for bbox in caption_blocks:
        caption_top = bbox[1]
        caption_left = bbox[0]
        caption_right = bbox[2]

        region_bottom = caption_top - REGION_PAD
        if region_bottom < page_rect.y0 + 20:
            continue

        text_above = []
        for block in text_dict["blocks"]:
            if block["type"] != 0:
                continue
            block_bottom = block["bbox"][3]
            if block_bottom < caption_top and block_bottom > page_rect.y0:
                text_above.append(block["bbox"])

        if text_above:
            text_above.sort(key=lambda b: b[3], reverse=True)
            region_top = page_rect.y0
            for tb in text_above:
                if tb[3] < caption_top - 20:
                    region_top = tb[3] + REGION_PAD
                    break
        else:
            region_top = page_rect.y0

        width = caption_right - caption_left
        center_x = (caption_left + caption_right) / 2
        region_left = max(page_rect.x0, center_x - width * 0.75)
        region_right = min(page_rect.x1, center_x + width * 0.75)
        region_left = min(region_left, caption_left - 20)
        region_right = max(region_right, caption_right + 20)

        clip = fitz.Rect(region_left, region_top, region_right, region_bottom)
        clip = clip & page_rect

        if clip.width < MIN_DIMENSION or clip.height < MIN_DIMENSION:
            continue

        pix = page.get_pixmap(clip=clip, dpi=RENDER_DPI)
        fig_counter += 1
        record = _save_image(pix, images_dir, page_num, fig_counter, seen_digests, "caption")
        if record:
            records.append(record)
            clip_rects.append(clip)

    return records, clip_rects, fig_counter


def _cluster_drawings(drawings, page_rect):
    if not drawings:
        return []

    rects = []
    for d in drawings:
        r = fitz.Rect(d["rect"])
        if r.is_empty or r.is_infinite:
            continue
        rects.append(r)

    if len(rects) < MIN_DRAWING_COMMANDS:
        return []

    rects.sort(key=lambda r: (r.y0, r.x0))

    clusters = []
    current = list(rects[0])
    count = 1

    for r in rects[1:]:
        if r.y0 <= current[3] + CLUSTER_GAP and r.x0 <= current[2] + CLUSTER_GAP:
            current[0] = min(current[0], r.x0)
            current[1] = min(current[1], r.y0)
            current[2] = max(current[2], r.x1)
            current[3] = max(current[3], r.y1)
            count += 1
        else:
            if count >= MIN_DRAWING_COMMANDS:
                clusters.append(fitz.Rect(current))
            current = list(r)
            count = 1

    if count >= MIN_DRAWING_COMMANDS:
        clusters.append(fitz.Rect(current))

    padded = []
    for c in clusters:
        c = c + fitz.Rect(-REGION_PAD, -REGION_PAD, REGION_PAD, REGION_PAD)
        c = c & page_rect
        if c.width >= MIN_DIMENSION and c.height >= MIN_DIMENSION:
            padded.append(c)

    return padded


def _find_drawing_figures(page, page_num, images_dir, fig_counter, seen_digests, existing_rects):
    records = []
    clip_rects = []

    try:
        drawings = page.get_drawings()
    except Exception:
        return records, clip_rects, fig_counter

    clusters = _cluster_drawings(drawings, page.rect)

    for clip in clusters:
        if _overlaps_any(clip, existing_rects):
            continue

        pix = page.get_pixmap(clip=clip, dpi=RENDER_DPI)
        fig_counter += 1
        record = _save_image(pix, images_dir, page_num, fig_counter, seen_digests, "drawing")
        if record:
            records.append(record)
            clip_rects.append(clip)

    return records, clip_rects, fig_counter


def _find_embedded_images(doc, page, page_num, images_dir, fig_counter, seen_digests):
    records = []
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

        fig_counter += 1
        record = _save_image(pix, images_dir, page_num, fig_counter, seen_digests, "embedded")
        if record:
            records.append(record)

    return records, fig_counter


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

        caption_records, caption_rects, fig_counter = _find_caption_figures(
            page, page_num, images_dir, fig_counter, seen_digests
        )
        image_records.extend(caption_records)

        drawing_records, drawing_rects, fig_counter = _find_drawing_figures(
            page, page_num, images_dir, fig_counter, seen_digests, caption_rects
        )
        image_records.extend(drawing_records)

        embedded_records, fig_counter = _find_embedded_images(
            doc, page, page_num, images_dir, fig_counter, seen_digests
        )
        image_records.extend(embedded_records)

    doc.close()

    output_path = state_dir / "images.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(image_records, f, ensure_ascii=False, indent=2)

    by_source = {}
    for r in image_records:
        s = r.get("source", "unknown")
        by_source[s] = by_source.get(s, 0) + 1

    print(json.dumps({
        "status": "ok",
        "imageCount": len(image_records),
        "bySource": by_source,
        "outputPath": str(output_path),
    }))
    return image_records


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <pdf_path> <output_dir>", file=sys.stderr)
        sys.exit(1)
    extract_images(sys.argv[1], sys.argv[2])
