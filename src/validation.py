import time
import threading
import json
from ollama import Client
from src.config import Config
from src.db import get_pending_validations, update_approval_status
from src import prompts

class ValidationManager:
    def __init__(self, interval: int = 10):
        self._interval = interval
        self._stop_event = threading.Event()
        self._worker_thread = None
        self._client = Client(host=Config.VALIDATION_LLM_URL)

    def start(self):
        if self._worker_thread is None:
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()
            print(f"🕵️ Validation module started. Thread ID: {self._worker_thread.ident}")

    def stop(self):
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join()

    def _worker(self):
        while not self._stop_event.is_set():
            try:
                pending = get_pending_validations(limit=10)
                if not pending:
                    time.sleep(self._interval)
                    continue

                for record in pending:
                    is_valid, notes = self._validate_record(record)
                    update_approval_status(record["id"], is_valid, notes)
                    print(f"🔍 Validated record {record['id']}: {'✅ Valid' if is_valid else '❌ Invalid'}")

            except Exception as e:
                print(f"⚠️ Validation worker encountered an error: {e}")
                time.sleep(self._interval)

    def _validate_record(self, record: dict) -> (bool, str):
        prompt = prompts.build_validation_prompt(
            source_text=record["value"],
            translated_text=record["translation"],
            source_lang=record["language"],
            target_lang=record["translation_language"]
        )
        try:
            response = self._client.chat(
                model=Config.VALIDATION_LLM,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},
            )
            content = response["message"]["content"].strip()
            # Basic cleanup if LLM adds markdown
            content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            return data.get("is_valid", False), data.get("reason", "")
        except Exception as e:
            # print(f"⚠️ Failed to validate record {record['id']}: {e}")
            return False, f"Validation failed: {e}"

# Global instance
validator = ValidationManager()
