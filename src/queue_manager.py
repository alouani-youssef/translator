import queue
import threading
import time
from typing import List, Dict, Any, Callable
from src.db import upsert_translation, bulk_upsert_translations

class QueueManager:
    def __init__(self, batch_size: int = 50, flush_interval: int = 5):
        self._queue = queue.Queue()
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._stop_event = threading.Event()
        self._worker_thread = None

    def start(self):
        if self._worker_thread is None:
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()
            print("🧵 Database queue worker started.")

    def stop(self):
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join()

    def push(self, record: Dict[str, Any]):
        self._queue.put(record)

    def push_batch(self, records: List[Dict[str, Any]]):
        for record in records:
            self._queue.put(record)

    def _worker(self):
        batch = []
        last_flush = time.time()

        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                # Try to get an item from the queue
                record = self._queue.get(timeout=1)
                batch.append(record)
                self._queue.task_done()
            except queue.Empty:
                pass

            # Check if we should flush
            should_flush = (
                len(batch) >= self._batch_size or 
                (time.time() - last_flush >= self._flush_interval and batch)
            )

            if should_flush:
                try:
                    bulk_upsert_translations(batch)
                    # print(f"💾 Flushed {len(batch)} records to DB.")
                except Exception as e:
                    print(f"⚠️ Queue worker failed to upsert batch: {e}")
                
                batch = []
                last_flush = time.time()

# Global instance
db_queue = QueueManager()
