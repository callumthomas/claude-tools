#!/usr/bin/env python3
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

KATEX_VERSION = "0.16.9"
KATEX_URL = (
    f"https://github.com/KaTeX/KaTeX/releases/download/"
    f"v{KATEX_VERSION}/katex.tar.gz"
)
CACHE_DIR = Path.home() / ".cache" / "pdf-simplifier" / "katex" / KATEX_VERSION

KATEX_HEAD_LOCAL = '  <link rel="stylesheet" href="katex/katex.min.css">'

KATEX_SCRIPTS_LOCAL = (
    '  <script src="katex/katex.min.js"></script>\n'
    '  <script src="katex/contrib/auto-render.min.js"></script>'
)


def download_katex():
    if (CACHE_DIR / "katex.min.js").exists():
        return CACHE_DIR

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tar_path = CACHE_DIR / "katex.tar.gz"

    print(f"Downloading KaTeX v{KATEX_VERSION}...", file=sys.stderr)
    urllib.request.urlretrieve(KATEX_URL, tar_path)

    with tarfile.open(tar_path) as tar:
        try:
            tar.extractall(CACHE_DIR, filter="data")
        except TypeError:
            tar.extractall(CACHE_DIR)

    tar_path.unlink()

    extracted = CACHE_DIR / "katex"
    if extracted.is_dir():
        for item in extracted.iterdir():
            dest = CACHE_DIR / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(item), str(dest))
        extracted.rmdir()

    return CACHE_DIR


def bundle_katex(output_dir):
    katex_dir = download_katex()
    dest = Path(output_dir) / "katex"
    dest.mkdir(exist_ok=True)

    for f in ["katex.min.js", "katex.min.css"]:
        shutil.copy2(katex_dir / f, dest / f)

    contrib_dest = dest / "contrib"
    contrib_dest.mkdir(exist_ok=True)
    shutil.copy2(
        katex_dir / "contrib" / "auto-render.min.js",
        contrib_dest / "auto-render.min.js",
    )

    fonts_src = katex_dir / "fonts"
    if fonts_src.exists():
        fonts_dest = dest / "fonts"
        fonts_dest.mkdir(exist_ok=True)
        for font_file in fonts_src.glob("*.woff2"):
            shutil.copy2(font_file, fonts_dest / font_file.name)


def render_template(template_dir, output_dir, title, has_math):
    template_dir = Path(template_dir)
    output_dir = Path(output_dir)

    if has_math:
        try:
            bundle_katex(output_dir)
            katex_head = KATEX_HEAD_LOCAL
            katex_scripts = KATEX_SCRIPTS_LOCAL
        except Exception as e:
            print(
                f"Warning: KaTeX download failed ({e}), using CDN",
                file=sys.stderr,
            )
            katex_head = (
                '  <link rel="stylesheet" href='
                f'"https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}'
                '/dist/katex.min.css">'
            )
            katex_scripts = (
                '  <script src="https://cdn.jsdelivr.net/npm/katex@'
                f'{KATEX_VERSION}/dist/katex.min.js"></script>\n'
                '  <script src="https://cdn.jsdelivr.net/npm/katex@'
                f'{KATEX_VERSION}/dist/contrib/auto-render.min.js">'
                "</script>"
            )
    else:
        katex_head = ""
        katex_scripts = ""

    html = (template_dir / "index.html").read_text()
    html = html.replace("{{TITLE}}", title)
    html = html.replace("{{KATEX_HEAD}}", katex_head)
    html = html.replace("{{KATEX_SCRIPTS}}", katex_scripts)
    (output_dir / "index.html").write_text(html)

    shutil.copy2(template_dir / "styles.css", output_dir / "styles.css")
    shutil.copy2(template_dir / "app.js", output_dir / "app.js")

    print(json.dumps({
        "status": "ok",
        "title": title,
        "hasMath": has_math,
        "katex": "local" if has_math else "none",
    }))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            f"Usage: {sys.argv[0]} <template_dir> <output_dir> <title> <has_math>",
            file=sys.stderr,
        )
        sys.exit(1)
    render_template(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4].lower() in ("true", "1", "yes"),
    )
