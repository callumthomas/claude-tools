#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

TEXT_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".csv", ".xml", ".html", ".htm", ".rst", ".tex", ".log"}
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".zsh", ".go", ".rs", ".rb", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt", ".scala", ".lua", ".pl", ".r", ".m", ".sql", ".zig", ".nim", ".ex", ".exs", ".clj", ".hs", ".ml", ".v", ".sv", ".vhd", ".tcl", ".asm", ".s", ".php", ".dart", ".vue", ".svelte", ".css", ".scss", ".sass", ".less", ".makefile", ".cmake", ".dockerfile"}


def estimate_file_tokens(filepath):
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return None

    words = len(content.split())
    characters = len(content)
    ext = filepath.suffix.lower()

    if ext in CODE_EXTENSIONS:
        method = "code"
        estimated_tokens = int(characters / 3.5)
    elif ext in TEXT_EXTENSIONS:
        method = "text"
        estimated_tokens = int(words * 1.3)
    else:
        method = "text"
        estimated_tokens = int(words * 1.3)

    return {
        "file": str(filepath.name) if filepath.parent == filepath else str(filepath),
        "words": words,
        "characters": characters,
        "estimated_tokens": estimated_tokens,
        "method": method,
    }


def process_path(target_path):
    files = []

    if target_path.is_file():
        result = estimate_file_tokens(target_path)
        if result:
            files.append(result)
    elif target_path.is_dir():
        for entry in sorted(target_path.rglob("*")):
            if entry.is_file():
                result = estimate_file_tokens(entry)
                if result:
                    relative = str(entry.relative_to(target_path))
                    result["file"] = relative
                    files.append(result)

    total = sum(f["estimated_tokens"] for f in files)

    return {
        "path": str(target_path.resolve()),
        "files": files,
        "total_estimated_tokens": total,
        "note": "Estimates are approximate. Use the Token Counting API for exact counts.",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Estimate token counts for files or directories using heuristics."
    )
    parser.add_argument(
        "path",
        help="Path to a file or directory to estimate tokens for",
    )
    args = parser.parse_args()

    target_path = Path(args.path)
    if not target_path.exists():
        print(f"Error: path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    result = process_path(target_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
