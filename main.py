import sys
import argparse
from pathlib import Path
from src.config import Config
from src.file_handler import translate_folder

def main():
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
        help=f"Input folder with JSON files (default: {Config.INPUT_FOLDER})",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=Config.OUTPUT_FOLDER,
        help=f"Output folder for translated files (default: {Config.OUTPUT_FOLDER})",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=Config.LLM_MODEL,
        help=f"Ollama model name (default: {Config.LLM_MODEL})",
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
        default=Config.LLM_URL,
        help=f"Ollama base URL (default: {Config.LLM_URL})",
    )

    args = parser.parse_args()
    Config.INPUT_FOLDER = args.input
    Config.OUTPUT_FOLDER = args.output
    Config.LLM_MODEL = args.model
    Config.TARGET_LANGUAGE = args.lang
    Config.OLLAMA_BASE_URL = args.url

    input_path = Path(Config.INPUT_FOLDER)
    if not input_path.exists():
        print(f"❌ Error: Input folder does not exist: {input_path}")
        sys.exit(1)

    if not input_path.is_dir():
        print(f"❌ Error: Input path is not a directory: {input_path}")
        sys.exit(1)

    try:
        success_count = translate_folder()
        sys.exit(0 if success_count > 0 else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Translation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()