import redis
import json
from typing import Any, Optional


class StateManager:
    def __init__(
        self,
        url: str,
        prefix: str = "app:"
    ):
        self.prefix = prefix
        self.client = redis.Redis.from_url(
            url,
            decode_responses=True
        )
    def _format_key(self, key: str) -> str:
        return f"{self.prefix}{key}"


    def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        try:
            formatted_key = self._format_key(key)
            serialized_value = json.dumps(value)

            return self.client.set(
                name=formatted_key,
                value=serialized_value,
                ex=expire
            )
        except Exception as e:
            print(f"[Redis SET Error] {e}")
            return False


    def get(self, key: str) -> Optional[Any]:
        try:
            formatted_key = self._format_key(key)
            value = self.client.get(formatted_key)

            if value is None:
                return None

            return json.loads(value)
        except Exception as e:
            print(f"[Redis GET Error] {e}")
            return None


    def delete(self, key: str) -> bool:
        try:
            return self.client.delete(self._format_key(key)) > 0
        except Exception as e:
            print(f"[Redis DELETE Error] {e}")
            return False

    def exists(self, key: str) -> bool:
        try:
            return self.client.exists(self._format_key(key)) == 1
        except Exception as e:
            print(f"[Redis EXISTS Error] {e}")
            return False

    def ttl(self, key: str) -> int:
        try:
            return self.client.ttl(self._format_key(key))
        except Exception as e:
            print(f"[Redis TTL Error] {e}")
            return -1

    def expire(self, key: str, seconds: int) -> bool:
        try:
            return self.client.expire(self._format_key(key), seconds)
        except Exception as e:
            print(f"[Redis EXPIRE Error] {e}")
            return False

    def incr(self, key: str) -> int:
        try:
            return self.client.incr(self._format_key(key))
        except Exception as e:
            print(f"[Redis INCR Error] {e}")
            return 0