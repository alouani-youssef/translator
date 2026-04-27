import sys
import argparse
from pathlib import Path

from src.config import Config
from src.file import translate_folder
from src.db import init_db
from src.queue_manager import db_queue
from args import parse_args, apply_config, validate_input_path



def run() -> int:
    args = parse_args()
    apply_config(args)

    try:
        validate_input_path(Config.INPUT_FOLDER)
        print("🗄️ Initializing database...")
        init_db()
        db_queue.start()
        print("🚀 Starting translation pipeline...")
        success_count = translate_folder()
        print("-" * 50)
        print(f"✅ Completed. Files translated: {success_count}")
        return 0 if success_count > 0 else 1
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️ Translation interrupted by user")
        return 130

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


def main() -> None:
    exit_code = run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()