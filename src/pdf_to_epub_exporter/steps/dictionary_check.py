from pathlib import Path

from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.dictionary import correct_text_by_dictionary, load_dictionary
from pdf_to_epub_exporter.step import PipelineStep


class DictionaryCheckStep(PipelineStep):
    step_id = "dictionary_check"

    def run(self, context: PipelineContext) -> None:
        text = context.merged_text or context.texts.get("scan_a", "") or context.texts.get("scan_b", "")
        if not text:
            context.corrected_text = ""
            context.add_warning("dictionary_check skipped: no text to process")
            return

        dictionary_file = self.params.get("dictionary_file", "resources/de_dictionary_sample.txt")
        dictionary_path = Path(dictionary_file)
        if not dictionary_path.exists():
            context.add_warning(f"dictionary file not found: {dictionary_file}")
            context.corrected_text = text
            return

        cutoff = float(self.params.get("cutoff", 0.85))
        dictionary = load_dictionary(str(dictionary_path))
        corrected, corrections = correct_text_by_dictionary(text, dictionary, cutoff=cutoff)

        context.corrected_text = corrected
        context.artifacts["dictionary_corrections"] = corrections
