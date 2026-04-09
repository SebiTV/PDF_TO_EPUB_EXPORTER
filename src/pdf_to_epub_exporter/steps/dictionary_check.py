from pathlib import Path
from collections import Counter
from datetime import datetime
from typing import Any

from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.dictionary import (
    correct_text_by_dictionary,
    correct_text_by_hunspell_and_wordfreq,
    load_dictionary,
)
from pdf_to_epub_exporter.step import PipelineStep


class DictionaryCheckStep(PipelineStep):
    step_id = "dictionary_check"

    @staticmethod
    def _get_count(diag: dict[str, Any], key: str) -> int:
        return int(diag.get(key, 0))

    @staticmethod
    def _join_examples(values: list[str]) -> str:
        return ", ".join(values) if values else "-"

    @staticmethod
    def _format_low_similarity_candidate_list(top_candidates: list[dict[str, Any]]) -> str:
        if not top_candidates:
            return "-"

        parts: list[str] = []
        for candidate in top_candidates[:2]:
            word = str(candidate.get("word", ""))
            score = float(candidate.get("score", 0.0))
            parts.append(f"{word} ({score:.3f})")
        return ", ".join(parts) if parts else "-"

    def run(self, context: PipelineContext) -> None:
        text = context.merged_text or context.texts.get("scan_a", "") or context.texts.get("scan_b", "")
        if not text:
            context.corrected_text = ""
            context.add_warning("dictionary_check skipped: no text to process")
            return

        corrected = text
        corrections: list[tuple[str, str]] = []
        diagnostics: dict[str, Any] = {}
        mode = "hunspell"

        # Preferred mode: Hunspell dictionary with wordfreq ranking.
        aff_path = str(self.params.get("hunspell_aff", "resources/hunspell/de_DE.aff"))
        dic_path = str(self.params.get("hunspell_dic", "resources/hunspell/de_DE.dic"))
        language = str(self.params.get("wordfreq_language", "de"))
        min_similarity = float(self.params.get("min_similarity", 0.75))
        use_wordfreq = bool(self.params.get("use_wordfreq_ranking", True))
        max_suggestions_to_score = int(self.params.get("max_suggestions_to_score", 40))

        try:
            corrected, corrections = correct_text_by_hunspell_and_wordfreq(
                text,
                aff_path=aff_path,
                dic_path=dic_path,
                language=language,
                min_similarity=min_similarity,
                use_wordfreq=use_wordfreq,
                max_suggestions_to_score=max_suggestions_to_score,
                diagnostics=diagnostics,
            )
        except Exception as exc:
            context.add_warning(f"hunspell mode unavailable, fallback active: {exc}")
            mode = "fallback_dictionary"

            dictionary_file = self.params.get("dictionary_file", "resources/de_dictionary_sample.txt")
            dictionary_path = Path(str(dictionary_file))
            if dictionary_path.exists():
                cutoff = float(self.params.get("cutoff", 0.85))
                dictionary = load_dictionary(str(dictionary_path))
                corrected, corrections = correct_text_by_dictionary(
                    text,
                    dictionary,
                    cutoff=cutoff,
                    diagnostics=diagnostics,
                )
            else:
                context.add_warning(
                    "fallback dictionary file not found; dictionary_check left text unchanged"
                )

        checked = self._get_count(diagnostics, "checked_tokens")
        recognized = self._get_count(diagnostics, "recognized_tokens")
        unknown = self._get_count(diagnostics, "unknown_tokens")
        corrected_count = self._get_count(diagnostics, "corrected_tokens")
        no_suggestion = self._get_count(diagnostics, "no_suggestion_tokens")
        low_similarity = self._get_count(diagnostics, "low_similarity_tokens")

        context.add_log(
            "dictionary_check summary: "
            f"mode={mode}, checked={checked}, recognized={recognized}, unknown={unknown}, "
            f"corrected={corrected_count}, unresolved={no_suggestion + low_similarity}"
        )

        pair_counter = Counter(corrections)
        top_n = int(self.params.get("log_top_corrections", 20))
        for (source, target), count in pair_counter.most_common(top_n):
            context.add_log(f"dictionary_check corrected: {source} -> {target} (x{count})")

        no_suggestion_examples = diagnostics.get("no_suggestion_examples", [])
        low_similarity_examples = diagnostics.get("low_similarity_examples", [])
        low_similarity_details = diagnostics.get("low_similarity_details", [])
        if no_suggestion_examples:
            context.add_log(
                "dictionary_check unresolved(no_suggestion): "
                f"{self._join_examples(no_suggestion_examples)}"
            )
        if low_similarity_details:
            context.add_log("dictionary_check unresolved(low_similarity):")
            for entry in low_similarity_details:
                token = str(entry.get("token", ""))
                formatted_candidates = self._format_low_similarity_candidate_list(
                    entry.get("top_candidates", [])
                )
                context.add_log(
                    f"dictionary_check low_similarity: {token} -> {formatted_candidates}"
                )
        elif low_similarity_examples:
            context.add_log(
                "dictionary_check unresolved(low_similarity): "
                f"{self._join_examples(low_similarity_examples)}"
            )

        context.corrected_text = corrected
        context.artifacts["dictionary_corrections"] = corrections
        context.artifacts["dictionary_diagnostics"] = diagnostics

        write_log_file = bool(self.params.get("write_log_file", True))
        if write_log_file:
            context.output_dir.mkdir(parents=True, exist_ok=True)
            log_file = str(self.params.get("log_file", f"{context.input_pdf.stem}.dictionary_check.log.txt"))
            log_path = context.output_dir / log_file

            lines: list[str] = [
                "Dictionary Check Report",
                f"generated_at={datetime.now().isoformat(timespec='seconds')}",
                f"mode={mode}",
                f"checked_tokens={checked}",
                f"recognized_tokens={recognized}",
                f"unknown_tokens={unknown}",
                f"corrected_tokens={corrected_count}",
                f"no_suggestion_tokens={no_suggestion}",
                f"low_similarity_tokens={low_similarity}",
                "",
                "Top corrections:",
            ]

            if pair_counter:
                for (source, target), count in pair_counter.most_common(top_n):
                    lines.append(f"- {source} -> {target} (x{count})")
            else:
                lines.append("- none")

            lines.extend(
                [
                    "",
                    "Unresolved examples (no suggestion):",
                    f"- {self._join_examples(no_suggestion_examples)}",
                    "",
                    "Unresolved examples (low similarity):",
                ]
            )

            if low_similarity_details:
                for entry in low_similarity_details:
                    token = str(entry.get("token", ""))
                    formatted_candidates = self._format_low_similarity_candidate_list(
                        entry.get("top_candidates", [])
                    )
                    lines.append(f"- {token} -> {formatted_candidates}")
            else:
                lines.append(f"- {self._join_examples(low_similarity_examples)}")

            log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            context.artifacts["dictionary_log_file"] = str(log_path)
            context.add_log(f"dictionary_check report written: {log_path}")
