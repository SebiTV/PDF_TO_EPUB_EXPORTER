from pdf_to_epub_exporter.registry import StepRegistry
from pdf_to_epub_exporter.steps.dictionary_check import DictionaryCheckStep
from pdf_to_epub_exporter.steps.export_epub import ExportEpubStep
from pdf_to_epub_exporter.steps.reconcile import ReconcileScansStep
from pdf_to_epub_exporter.steps.scan_a import ScanAStep
from pdf_to_epub_exporter.steps.scan_b import ScanBStep


def build_default_registry() -> StepRegistry:
    registry = StepRegistry()
    registry.register(ScanAStep.step_id, ScanAStep)
    registry.register(ScanBStep.step_id, ScanBStep)
    registry.register(ReconcileScansStep.step_id, ReconcileScansStep)
    registry.register(DictionaryCheckStep.step_id, DictionaryCheckStep)
    registry.register(ExportEpubStep.step_id, ExportEpubStep)
    return registry
