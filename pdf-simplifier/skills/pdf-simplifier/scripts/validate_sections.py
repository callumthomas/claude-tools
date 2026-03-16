#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ["id", "title", "full", "medium", "eli5", "agentNotes"]


def validate_sections(output_dir):
    state_dir = Path(output_dir) / ".state"

    with open(state_dir / "content-shell.json") as f:
        shell = json.load(f)

    expected_ids = []
    for ch in shell["chapters"]:
        for section in ch["sections"]:
            expected_ids.append(section["id"])

    errors = []
    valid = 0

    for section_id in expected_ids:
        path = state_dir / "sections" / f"{section_id}.json"

        if not path.exists():
            errors.append(f"Missing: {section_id}.json")
            continue

        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in {section_id}.json: {e}")
            continue

        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            errors.append(f"{section_id}.json missing fields: {', '.join(missing)}")
            continue

        if not isinstance(data["agentNotes"], list):
            errors.append(f"{section_id}.json: agentNotes is not a list")
            continue

        valid += 1

    result = {
        "status": "ok" if not errors else "errors",
        "valid": valid,
        "total": len(expected_ids),
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return len(errors) == 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output_dir>", file=sys.stderr)
        sys.exit(1)
    ok = validate_sections(sys.argv[1])
    sys.exit(0 if ok else 1)
