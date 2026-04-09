import difflib
import re
from pathlib import Path
from typing import Any


WORD_PATTERN = re.compile(r"[A-Za-zÄÖÜäöüß0-9']+")
HYPHENATED_LINEBREAK_PATTERN = re.compile(r"([A-Za-zÄÖÜäöüß0-9']+)-(\r?\n)([A-Za-zÄÖÜäöüß0-9']+)")


def _is_word_like_token(token: str) -> bool:
    # Skip pure numbers, but keep alphanumeric OCR words like "da8".
    return any(char.isalpha() for char in token)


def _init_diagnostics(diagnostics: dict[str, Any] | None) -> dict[str, Any] | None:
    if diagnostics is None:
        return None

    diagnostics.setdefault("checked_tokens", 0)
    diagnostics.setdefault("recognized_tokens", 0)
    diagnostics.setdefault("unknown_tokens", 0)
    diagnostics.setdefault("corrected_tokens", 0)
    diagnostics.setdefault("no_suggestion_tokens", 0)
    diagnostics.setdefault("low_similarity_tokens", 0)
    diagnostics.setdefault("corrected_examples", [])
    diagnostics.setdefault("no_suggestion_examples", [])
    diagnostics.setdefault("low_similarity_examples", [])
    diagnostics.setdefault("low_similarity_details", [])
    return diagnostics


def _add_example(target: list[str], value: str, limit: int = 25) -> None:
    if len(target) < limit and value not in target:
        target.append(value)


def _add_correction_example(target: list[tuple[str, str]], source: str, fixed: str, limit: int = 25) -> None:
    if len(target) < limit and (source, fixed) not in target:
        target.append((source, fixed))


def _render_hyphenated_result(
    corrected_word: str,
    split_index: int,
    newline: str,
    original_left: str,
    original_right: str,
) -> str:
    if len(corrected_word) < 2:
        return f"{original_left}-{newline}{original_right}"

    adjusted = min(max(1, split_index), len(corrected_word) - 1)
    return f"{corrected_word[:adjusted]}-{newline}{corrected_word[adjusted:]}"


def _protect_hyphenated_linebreak_words(
    text: str,
    token_corrector,
) -> tuple[str, dict[str, str]]:
    protected_segments: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        left = match.group(1)
        newline = match.group(2)
        right = match.group(3)
        combined = f"{left}{right}"
        corrected_combined = token_corrector(combined)

        if corrected_combined == combined:
            rendered = f"{left}-{newline}{right}"
        else:
            rendered = _render_hyphenated_result(
                corrected_combined,
                len(left),
                newline,
                left,
                right,
            )

        placeholder = f"@@{len(protected_segments)}@@"
        protected_segments[placeholder] = rendered
        return placeholder

    return HYPHENATED_LINEBREAK_PATTERN.sub(replace, text), protected_segments


def _restore_protected_segments(text: str, protected_segments: dict[str, str]) -> str:
    restored = text
    for placeholder, rendered in protected_segments.items():
        restored = restored.replace(placeholder, rendered)
    return restored


def _add_low_similarity_detail(
    target: list[dict[str, Any]],
    token: str,
    top_candidates: list[tuple[str, float]],
    limit: int = 25,
) -> None:
    if any(entry.get("token") == token for entry in target):
        return
    if len(target) >= limit:
        return
    target.append(
        {
            "token": token,
            "top_candidates": [
                {"word": word, "score": score} for word, score in top_candidates[:2]
            ],
        }
    )


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


def _generate_ocr_variants(token: str, limit: int = 16) -> list[str]:
    queue: list[str] = [token]
    seen = {token}
    variants: list[str] = []

    replacements: list[tuple[str, str]] = [
        ("ii", "ü"),
        ("aa", "ä"),
        ("oo", "ö"),
        ("uu", "ü"),
        ("8", "ß"),
        ("0", "o"),
        ("1", "l"),
        ("1", "i"),
        ("rn", "m"),
        ("m", "rn"),
        ("cl", "d"),
        ("vv", "w"),
    ]
    if "B" in token:
        replacements.append(("B", "ß"))

    while queue and len(variants) < limit:
        current = queue.pop(0)
        current_lower = current.lower()

        for old, new in replacements:
            if old in {"B", "8", "0", "1"}:
                if old not in current:
                    continue
                start = 0
                while True:
                    index = current.find(old, start)
                    if index == -1:
                        break
                    candidate = current[:index] + new + current[index + len(old) :]
                    if candidate not in seen:
                        seen.add(candidate)
                        variants.append(candidate)
                        queue.append(candidate)
                        if len(variants) >= limit:
                            return variants
                    start = index + 1
            else:
                if old not in current_lower:
                    continue
                start = 0
                while True:
                    index = current_lower.find(old, start)
                    if index == -1:
                        break
                    candidate = current[:index] + new + current[index + len(old) :]
                    if candidate not in seen:
                        seen.add(candidate)
                        variants.append(candidate)
                        queue.append(candidate)
                        if len(variants) >= limit:
                            return variants
                    start = index + 1
                continue

    return variants


def _find_exact_variant_match(token: str, is_known) -> str | None:
    for variant in _generate_ocr_variants(token):
        normalized_variant = variant.lower()
        if is_known(normalized_variant):
            return _case_like(token, normalized_variant)

        # If dictionaries only contain ss-orthography, still allow OCR fix to output ß.
        if "ß" in normalized_variant and is_known(normalized_variant.replace("ß", "ss")):
            return _case_like(token, normalized_variant)
    return None


def correct_text_by_dictionary(
    text: str,
    dictionary: set[str],
    cutoff: float = 0.85,
    diagnostics: dict[str, Any] | None = None,
) -> tuple[str, list[tuple[str, str]]]:
    corrections: list[tuple[str, str]] = []
    diag = _init_diagnostics(diagnostics)
    suggestion_cache: dict[str, str | None] = {}
    variant_cache: dict[str, str | None] = {}

    def correct_token(token: str) -> str:
        if not _is_word_like_token(token):
            return token

        normalized = token.lower()
        if diag is not None:
            diag["checked_tokens"] += 1

        if normalized in dictionary:
            if diag is not None:
                diag["recognized_tokens"] += 1
            return token

        if diag is not None:
            diag["unknown_tokens"] += 1

        if token not in variant_cache:
            variant_cache[token] = _find_exact_variant_match(token, lambda word: word in dictionary)

        cached_variant = variant_cache[token]
        if cached_variant is not None:
            corrections.append((token, cached_variant))
            if diag is not None:
                diag["corrected_tokens"] += 1
                _add_correction_example(diag["corrected_examples"], token, cached_variant)
            return cached_variant

        if normalized not in suggestion_cache:
            candidates = difflib.get_close_matches(normalized, dictionary, n=1, cutoff=cutoff)
            suggestion_cache[normalized] = candidates[0] if candidates else None

        cached_candidate = suggestion_cache[normalized]
        if cached_candidate is None:
            if diag is not None:
                diag["no_suggestion_tokens"] += 1
                _add_example(diag["no_suggestion_examples"], token)
            return token

        corrected = _case_like(token, cached_candidate)
        if corrected != token:
            corrections.append((token, corrected))
            if diag is not None:
                diag["corrected_tokens"] += 1
                _add_correction_example(diag["corrected_examples"], token, corrected)
        return corrected

    protected_text, protected_segments = _protect_hyphenated_linebreak_words(text, correct_token)
    corrected_text = WORD_PATTERN.sub(lambda match: correct_token(match.group(0)), protected_text)
    corrected_text = _restore_protected_segments(corrected_text, protected_segments)
    return corrected_text, corrections


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _rank_with_wordfreq(
    candidates: list[str],
    token: str,
    language: str,
    use_wordfreq: bool,
    score_cache: dict[tuple[str, str, str], float],
    freq_cache: dict[tuple[str, str], float],
    sim_cache: dict[tuple[str, str], float],
) -> list[str]:
    token_l = token.lower()
    scored: list[tuple[str, float]] = []

    if not use_wordfreq:
        for word in candidates:
            word_l = word.lower()
            sim_key = (token_l, word_l)
            if sim_key not in sim_cache:
                sim_cache[sim_key] = _similarity(token_l, word_l)
            scored.append((word, sim_cache[sim_key]))
        return [word for word, _ in sorted(scored, key=lambda pair: pair[1], reverse=True)]

    try:
        from wordfreq import zipf_frequency
    except Exception:
        return _rank_with_wordfreq(
            candidates,
            token,
            language,
            False,
            score_cache,
            freq_cache,
            sim_cache,
        )

    for word in candidates:
        word_l = word.lower()
        score_key = (token_l, word_l, language)
        if score_key in score_cache:
            scored.append((word, score_cache[score_key]))
            continue

        sim_key = (token_l, word_l)
        if sim_key not in sim_cache:
            sim_cache[sim_key] = _similarity(token_l, word_l)
        sim = sim_cache[sim_key]

        freq_key = (word_l, language)
        if freq_key not in freq_cache:
            freq_cache[freq_key] = max(0.0, float(zipf_frequency(word, language))) / 8.0
        freq = freq_cache[freq_key]

        combined = (sim * 0.8) + (freq * 0.2)
        score_cache[score_key] = combined
        scored.append((word, combined))

    ranked = sorted(scored, key=lambda pair: pair[1], reverse=True)
    return [word for word, _ in ranked]


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
    use_wordfreq: bool = True,
    max_suggestions_to_score: int = 40,
    diagnostics: dict[str, Any] | None = None,
) -> tuple[str, list[tuple[str, str]]]:
    checker = _load_spylls_dictionary(aff_path, dic_path)
    corrections: list[tuple[str, str]] = []
    diag = _init_diagnostics(diagnostics)
    suggestion_cache: dict[str, str | None] = {}
    low_similarity_cache: dict[str, list[tuple[str, float]]] = {}
    known_cache: dict[str, bool] = {}
    variant_cache: dict[str, str | None] = {}
    rank_score_cache: dict[tuple[str, str, str], float] = {}
    freq_cache: dict[tuple[str, str], float] = {}
    sim_cache: dict[tuple[str, str], float] = {}

    capped_suggestion_count = max(1, int(max_suggestions_to_score))

    def correct_token(token: str) -> str:
        if not _is_word_like_token(token):
            return token

        normalized = token.lower()
        if diag is not None:
            diag["checked_tokens"] += 1

        if normalized not in known_cache:
            known_cache[normalized] = bool(checker.lookup(normalized))

        if known_cache[normalized]:
            if diag is not None:
                diag["recognized_tokens"] += 1
            return token

        if diag is not None:
            diag["unknown_tokens"] += 1

        if token not in variant_cache:
            variant_cache[token] = _find_exact_variant_match(
                token,
                lambda word: known_cache.setdefault(word, bool(checker.lookup(word))),
            )

        cached_variant = variant_cache[token]
        if cached_variant is not None:
            corrections.append((token, cached_variant))
            if diag is not None:
                diag["corrected_tokens"] += 1
                _add_correction_example(diag["corrected_examples"], token, cached_variant)
            return cached_variant

        if normalized not in suggestion_cache:
            raw_suggestions = list(checker.suggest(normalized))
            if len(raw_suggestions) > capped_suggestion_count:
                raw_suggestions = raw_suggestions[:capped_suggestion_count]
            if not raw_suggestions:
                suggestion_cache[normalized] = None
            else:
                scored_suggestions = sorted(
                    [
                        (
                            s,
                            sim_cache.setdefault((normalized, s.lower()), _similarity(normalized, s.lower())),
                        )
                        for s in raw_suggestions
                    ],
                    key=lambda pair: pair[1],
                    reverse=True,
                )
                filtered = [s for s, score in scored_suggestions if score >= min_similarity]
                if not filtered:
                    suggestion_cache[normalized] = ""
                    low_similarity_cache[normalized] = scored_suggestions[:2]
                else:
                    ranked = _rank_with_wordfreq(
                        filtered,
                        normalized,
                        language,
                        use_wordfreq,
                        rank_score_cache,
                        freq_cache,
                        sim_cache,
                    )
                    suggestion_cache[normalized] = ranked[0]

        cached_suggestion = suggestion_cache[normalized]
        if cached_suggestion is None:
            if diag is not None:
                diag["no_suggestion_tokens"] += 1
                _add_example(diag["no_suggestion_examples"], token)
            return token

        if cached_suggestion == "":
            if diag is not None:
                diag["low_similarity_tokens"] += 1
                _add_example(diag["low_similarity_examples"], token)
                _add_low_similarity_detail(
                    diag["low_similarity_details"],
                    token,
                    low_similarity_cache.get(normalized, []),
                )
            return token

        best = cached_suggestion
        corrected = _case_like(token, best)
        if corrected != token:
            corrections.append((token, corrected))
            if diag is not None:
                diag["corrected_tokens"] += 1
                _add_correction_example(diag["corrected_examples"], token, corrected)
        return corrected

    protected_text, protected_segments = _protect_hyphenated_linebreak_words(text, correct_token)
    corrected_text = WORD_PATTERN.sub(lambda match: correct_token(match.group(0)), protected_text)
    corrected_text = _restore_protected_segments(corrected_text, protected_segments)
    return corrected_text, corrections
