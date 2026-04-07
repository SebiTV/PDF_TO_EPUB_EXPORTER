import argparse
from pathlib import Path

from pdf_to_epub_exporter.config import load_config
from pdf_to_epub_exporter.context import PipelineContext
from pdf_to_epub_exporter.pipeline import Pipeline
from pdf_to_epub_exporter.steps import build_default_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Modular PDF to EPUB exporter")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run configured pipeline")
    run_cmd.add_argument("--pdf", required=True, help="Input PDF file")
    run_cmd.add_argument("--output", required=True, help="Output directory")
    run_cmd.add_argument("--config", required=True, help="Path to pipeline config JSON")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "run":
        parser.error("Unsupported command")

    input_pdf = Path(args.pdf)
    output_dir = Path(args.output)
    config_path = Path(args.config)

    config = load_config(config_path)
    registry = build_default_registry()
    steps = registry.create_steps(config["steps"])

    context = PipelineContext(
        input_pdf=input_pdf,
        output_dir=output_dir,
        config=config,
    )

    pipeline = Pipeline(steps)
    result = pipeline.run(context)

    print("Pipeline logs:")
    for line in result.logs:
        print(f"  - {line}")

    if result.warnings:
        print("Warnings:")
        for line in result.warnings:
            print(f"  - {line}")

    print("Done.")
    return 0
