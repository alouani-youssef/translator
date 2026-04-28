import json
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from lib.json import translate_file_content
from lib.state import StateManager


state =  StateManager(url=Config.REDIS_URL)

def scan_input_folder() -> list[Path]:
    input_dir = Path(Config.INPUT_FOLDER)

    if not input_dir.exists():
        print(f"❌ Input folder does not exist: {input_dir}")
        return []

    json_files = sorted(input_dir.glob("*.json"))

    print(f"✅ Found {len(json_files)} JSON file(s)")
    return json_files


def load_json(file_path: Path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error reading {file_path.name}: {e}")
        return None


def save_json(file_path: Path, data):
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        print(f"❌ Error writing {file_path.name}: {e}")
        return False



def translate_file(input_path: Path, output_path: Path) -> bool:
    print(f"📄 {input_path.name}")

    data = load_json(input_path)
    if data is None:
        return False

    try:
        translated = translate_file_content(
            input_path.name,
            data,
            state=state,
            output_path=output_path
        )

        return True # The file is already saved incrementally

    except Exception as e:
        print(f"❌ Failed {input_path.name}: {e}")
        return False

def translate_folder() -> int:
    print(f"\n{'='*60}")
    print(f"📂 Input:  {Config.INPUT_FOLDER}")
    print(f"📂 Output: {Config.OUTPUT_FOLDER}")
    print(f"🧵 Workers: {Config.MAX_WORKERS}")
    print(f"{'='*60}\n")

    start_time = datetime.now()

    files = scan_input_folder()
    if not files:
        return 0

    output_dir = Path(Config.OUTPUT_FOLDER)

    success_count = 0

    with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                translate_file,
                f,
                output_dir / f.name
            ): f
            for f in files
        }

        for future in as_completed(futures):
            if future.result():
                success_count += 1

    elapsed = datetime.now() - start_time

    print(f"\n✅ Done: {success_count}/{len(files)} in {elapsed}\n")

    return success_count