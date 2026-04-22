import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import Config
from src.json_walker import walk


def scan_input_folder() -> list[Path]:
    # ... existing code ...
    input_dir = Path(Config.INPUT_FOLDER)

    if not input_dir.exists():
        print(f"❌ Input folder does not exist: {input_dir}")
        return []

    json_files = list(input_dir.glob("*.json"))

    if not json_files:
        print(f"⚠️  No JSON files found in: {input_dir}")
        return []

    print(f"✅ Found {len(json_files)} JSON file(s)")
    return sorted(json_files)


def load_json(file_path: Path) -> dict | list | None:
    # ... existing code ...
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON decode error: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return None


def save_json(file_path: Path, data: dict | list) -> bool:
    # ... existing code ...
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"  ❌ Error writing file: {e}")
        return False


def translate_file(input_path: Path, output_path: Path) -> bool:
    # ... existing code ...
    print(f"\n📄 Processing: {input_path.name}")

    data = load_json(input_path)
    if data is None:
        return False

    print(f"  🔄 Translating Process Starts for {input_path.name}...")
    translated = walk(data)
    print(f"Translating Process finish from {input_path.name} to {output_path.name}")
    success = save_json(output_path, translated)
    if success:
        print(f"  ✅ Saved to: {output_path}")
    return success


def translate_folder() -> int:
    print(f"📂 Input folder: {Config.INPUT_FOLDER}")
    print(f"📂 Output folder: {Config.OUTPUT_FOLDER}")
    print(f"🌐 Target language: {Config.TARGET_LANGUAGE}")
    print(f"🤖 Model: {Config.LLM_MODEL}")
    print(f"🧵 Parallel Workers: {Config.MAX_WORKERS}")
    print()

    json_files = scan_input_folder()
    if not json_files:
        return 0

    output_dir = Path(Config.OUTPUT_FOLDER)
    success_count = 0

    print(f"🚀 Starting translation with {Config.MAX_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
        future_to_file = {
            executor.submit(translate_file, json_file, output_dir / json_file.name): json_file
            for json_file in json_files
        }

        for future in as_completed(future_to_file):
            json_file = future_to_file[future]
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                print(f"  ❌ File {json_file.name} generated an exception: {e}")

    print(f"\n🎉 Done! Successfully translated {success_count}/{len(json_files)} file(s)")
    return success_count