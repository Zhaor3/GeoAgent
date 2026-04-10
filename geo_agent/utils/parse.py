from __future__ import annotations

import json
import re


def extract_json_object(raw: str) -> dict:
    return _extract(raw, "{", "}")


def extract_json_array(raw: str) -> list:
    return _extract(raw, "[", "]")


def get_text_from_response(response) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def _sanitize_json(text: str) -> str:
    # Remove single-line comments (// ...)
    text = re.sub(r'//[^\n]*', '', text)
    # Remove multi-line comments (/* ... */)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text


def _try_parse(text: str):
    # Try raw first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try after sanitizing
    try:
        return json.loads(_sanitize_json(text))
    except json.JSONDecodeError:
        pass
    return None


def _extract(raw: str, open_char: str, close_char: str):
    text = raw.strip()

    # Strip markdown fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part.strip()
            # Remove language tag like "json"
            if re.match(r"^[a-zA-Z]+[\s\n]", candidate):
                candidate = re.split(r'[\s\n]', candidate, maxsplit=1)[1] if re.search(r'[\s\n]', candidate) else candidate
                candidate = candidate.strip()
            if candidate and candidate[0] == open_char:
                result = _try_parse(candidate)
                if result is not None:
                    return result

    # Find the outermost matching brackets
    start = text.find(open_char)
    if start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    result = _try_parse(candidate)
                    if result is not None:
                        return result
                    break

    # Last resort — sanitize the whole text and try
    result = _try_parse(text)
    if result is not None:
        return result

    raise ValueError(f"Could not extract valid JSON from response (length={len(raw)})")
