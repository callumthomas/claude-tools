#!/usr/bin/env python3

import re
from pathlib import Path

TEXT_EXTENSIONS = {
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
    ".csv", ".xml", ".html", ".htm", ".rst", ".tex", ".log",
}
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".zsh", ".go",
    ".rs", ".rb", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".kt", ".scala", ".lua", ".pl", ".r", ".m", ".sql", ".zig", ".nim",
    ".ex", ".exs", ".clj", ".hs", ".ml", ".v", ".sv", ".vhd", ".tcl",
    ".asm", ".s", ".php", ".dart", ".vue", ".svelte", ".css", ".scss",
    ".sass", ".less", ".makefile", ".cmake", ".dockerfile",
}


def estimate_tokens_text(text):
    return int(len(text.split()) * 1.3)


def estimate_tokens_code(text):
    return int(len(text) / 3.5)


def estimate_tokens_file(filepath):
    filepath = Path(filepath)
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return 0
    ext = filepath.suffix.lower()
    if ext in CODE_EXTENSIONS:
        return estimate_tokens_code(content)
    return estimate_tokens_text(content)


def is_kebab_case(text):
    return bool(re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", text))


def split_frontmatter(content):
    parts = content.split("---", 2)
    if len(parts) >= 3:
        return parts[1].strip(), parts[2].strip()
    return "", content.strip()


def parse_frontmatter(content):
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content, ""

    raw_frontmatter = parts[1].strip()
    body = parts[2]

    frontmatter = {}
    current_key = None
    current_value_lines = []

    for line in raw_frontmatter.splitlines():
        simple_match = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if simple_match:
            if current_key:
                frontmatter[current_key] = "\n".join(current_value_lines).strip()
            current_key = simple_match.group(1)
            value = simple_match.group(2).strip()
            if value == ">" or value == "|":
                current_value_lines = []
            else:
                current_value_lines = [value]
        elif current_key and (line.startswith("  ") or line.startswith("\t") or line.strip() == ""):
            current_value_lines.append(line.strip())

    if current_key:
        frontmatter[current_key] = "\n".join(current_value_lines).strip()

    return frontmatter, body, raw_frontmatter


def parse_frontmatter_fields(content, keys=None):
    if keys is None:
        keys = ["name", "description", "model", "tools", "maxTurns", "max_turns"]
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    raw = parts[1]
    fields = {}
    for key in keys:
        pattern = rf"^{key}:\s*(.+?)(?:\n\S|\Z)"
        match = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value.startswith(">"):
                value = value[1:].strip()
            value = re.sub(r"\s+", " ", value)
            fields[key] = value
    return fields


def has_xml_brackets(text):
    for line in text.splitlines():
        cleaned = re.sub(r":\s*[>|]\s*$", "", line)
        if re.search(r"[<>]", cleaned):
            return True
    return False


def find_section(body, match_text):
    lines = body.split("\n")
    step_pattern = re.compile(r"^#{1,4}\s+(Step\s+\d+|Phase\s+\d+|\d+\.)", re.IGNORECASE)
    current_section = "Body"
    match_lower = match_text.lower()
    for line in lines:
        step_match = step_pattern.match(line)
        if step_match:
            current_section = line.strip().lstrip("#").strip()
        if match_lower in line.lower():
            return current_section
    return current_section


def has_nearby_keywords(body, match_pos, keywords, window=200):
    start = max(0, match_pos - window)
    end = min(len(body), match_pos + window)
    context = body[start:end].lower()
    return any(kw in context for kw in keywords)
