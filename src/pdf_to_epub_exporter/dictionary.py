import difflib
import re
from pathlib import Path


WORD_PATTERN = re.compile(r"[A-Za-zÄÖÜäöüß']+")


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

    corrected_text = WORD_PATTERN.sub(replace, text)
    return corrected_text, corrections


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _rank_with_wordfreq(candidates: list[str], token: str, language: str) -> list[str]:
    try:
        from wordfreq import zipf_frequency
    except Exception:
        return candidates

    token_l = token.lower()

    def score(word: str) -> float:
        sim = _similarity(token_l, word.lower())
        freq = max(0.0, float(zipf_frequency(word, language))) / 8.0
        return (sim * 0.8) + (freq * 0.2)

    ranked = sorted(candidates, key=score, reverse=True)
    return ranked


def _load_spylls_dictionary(aff_path: str, dic_path: str):
    from spylls.hunspell import Dictionary as SpyllsDictionary

    aff = Path(aff_path)
    dic = Path(dic_path)
    if not aff.exists() or not dic.exists():
        raise FileNotFoundError(f"Hunspell files missing: {aff_path}, {dic_path}")

    return SpyllsDictionary.from_files(str(dic.with_suffix("")))


def correct_text_by_hunspell_and_wordfreq(
    text: str,
    *,
    aff_path: str,
    dic_path: str,
    language: str = "de",
    min_similarity: float = 0.75,
) -> tuple[str, list[tuple[str, str]]]:
    checker = _load_spylls_dictionary(aff_path, dic_path)
    corrections: list[tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        normalized = token.lower()

        if checker.lookup(normalized):
            return token

        raw_suggestions = list(checker.suggest(normalized))
        if not raw_suggestions:
            return token

        filtered = [s for s in raw_suggestions if _similarity(normalized, s.lower()) >= min_similarity]
        if not filtered:
            return token

        ranked = _rank_with_wordfreq(filtered, normalized, language)
        best = ranked[0]
        corrected = _case_like(token, best)
        if corrected != token:
            corrections.append((token, corrected))
        return corrected

    corrected_text = WORD_PATTERN.sub(replace, text)
    return corrected_text, corrections
