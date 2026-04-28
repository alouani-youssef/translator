import argparse
from pathlib import Path
from config import Config

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate JSON files to a target language using Ollama",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --input ./my_jsons --output ./translated
  python main.py --model mistral --lang Spanish
        """,
    )

    parser.add_argument(
        "--input",
        type=str,
        default=Config.INPUT_FOLDER,
        help=f"Input folder (default: {Config.INPUT_FOLDER})",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=Config.OUTPUT_FOLDER,
        help=f"Output folder (default: {Config.OUTPUT_FOLDER})",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=Config.TRANSLATION_LLM,
        help=f"Ollama model (default: {Config.TRANSLATION_LLM})",
    )

    parser.add_argument(
        "--lang",
        type=str,
        default=Config.TARGET_LANGUAGE,
        help=f"Target language (default: {Config.TARGET_LANGUAGE})",
    )

    parser.add_argument(
        "--url",
        type=str,
        default=Config.TRANSLATION_LLM_URL,
        help=f"Ollama base URL (default: {Config.TRANSLATION_LLM_URL})",
    )

    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=Config.MAX_WORKERS,
        help=f"Parallel workers (default: {Config.MAX_WORKERS})",
    )

    return parser.parse_args()


def apply_config(args: argparse.Namespace) -> None:
    Config.INPUT_FOLDER = args.input
    Config.OUTPUT_FOLDER = args.output
    Config.TRANSLATION_LLM = args.model
    Config.TARGET_LANGUAGE = args.lang
    Config.OLLAMA_BASE_URL = args.url
    Config.MAX_WORKERS = args.workers


def validate_input_path(path: str) -> Path:
    input_path = Path(path)

    if not input_path.exists():
        raise ValueError(f"Input folder does not exist: {input_path}")

    if not input_path.is_dir():
        raise ValueError(f"Input path is not a directory: {input_path}")

    return input_path


