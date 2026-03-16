#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def assemble_content(output_dir):
    state = Path(output_dir) / ".state"

    with open(state / "content-shell.json") as f:
        shell = json.load(f)

    for chapter in shell["chapters"]:
        for section in chapter["sections"]:
            section_file = state / "sections" / f"{section['id']}.json"
            if section_file.exists():
                with open(section_file) as f:
                    data = json.load(f)
                section["full"] = data.get("full", section.get("full", ""))
                section["medium"] = data.get("medium", "")
                section["eli5"] = data.get("eli5", "")
                section["agentNotes"] = data.get("agentNotes", [])

    output_path = Path(output_dir) / "content.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(shell, f, ensure_ascii=False, indent=2)

    total = sum(len(ch["sections"]) for ch in shell["chapters"])
    print(json.dumps({
        "status": "ok",
        "sections": total,
        "outputPath": str(output_path),
    }))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output_dir>", file=sys.stderr)
        sys.exit(1)
    assemble_content(sys.argv[1])
