import difflib
import re


def load_dictionary(path: str) -> set[str]:
    with open(path, "r", encoding="utf-8") as handle:
        entries = {line.strip().lower() for line in handle if line.strip()}
    return entries


def _case_like(source: str, target: str) -> str:
    if source.isupper():
        return target.upper()
    if source[:1].isupper():
        return target.capitalize()
    return target


def correct_text_by_dictionary(text: str, dictionary: set[str], cutoff: float = 0.85) -> tuple[str, list[tuple[str, str]]]:
    pattern = re.compile(r"[A-Za-z']+")
    corrections: list[tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        normalized = token.lower()
        if normalized in dictionary:
            return token

        candidates = difflib.get_close_matches(normalized, dictionary, n=1, cutoff=cutoff)
        if not candidates:
            return token

        corrected = _case_like(token, candidates[0])
        if corrected != token:
            corrections.append((token, corrected))
        return corrected

    corrected_text = pattern.sub(replace, text)
    return corrected_text, corrections
