from pathlib import Path

from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.dictionary import (
    correct_text_by_dictionary,
    correct_text_by_hunspell_and_wordfreq,
    load_dictionary,
)
from pdf_to_epub_exporter.step import PipelineStep


class DictionaryCheckStep(PipelineStep):
    step_id = "dictionary_check"

    def run(self, context: PipelineContext) -> None:
        text = context.merged_text or context.texts.get("scan_a", "") or context.texts.get("scan_b", "")
        if not text:
            context.corrected_text = ""
            context.add_warning("dictionary_check skipped: no text to process")
            return

        corrected = text
        corrections: list[tuple[str, str]] = []

        # Preferred mode: Hunspell dictionary with wordfreq ranking.
        aff_path = str(self.params.get("hunspell_aff", "resources/hunspell/de_DE.aff"))
        dic_path = str(self.params.get("hunspell_dic", "resources/hunspell/de_DE.dic"))
        language = str(self.params.get("wordfreq_language", "de"))
        min_similarity = float(self.params.get("min_similarity", 0.75))

        try:
            corrected, corrections = correct_text_by_hunspell_and_wordfreq(
                text,
                aff_path=aff_path,
                dic_path=dic_path,
                language=language,
                min_similarity=min_similarity,
            )
        except Exception as exc:
            context.add_warning(f"hunspell mode unavailable, fallback active: {exc}")

            dictionary_file = self.params.get("dictionary_file", "resources/de_dictionary_sample.txt")
            dictionary_path = Path(str(dictionary_file))
            if dictionary_path.exists():
                cutoff = float(self.params.get("cutoff", 0.85))
                dictionary = load_dictionary(str(dictionary_path))
                corrected, corrections = correct_text_by_dictionary(text, dictionary, cutoff=cutoff)
            else:
                context.add_warning(
                    "fallback dictionary file not found; dictionary_check left text unchanged"
                )

        context.corrected_text = corrected
        context.artifacts["dictionary_corrections"] = corrections
