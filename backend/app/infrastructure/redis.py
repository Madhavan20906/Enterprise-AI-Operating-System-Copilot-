import redis
from app.config import settings

class RedisClient:
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        return self.client.set(key, value, ex=ex)

    def delete(self, key: str) -> int:
        return self.client.delete(key)

    def keys(self, pattern: str) -> list[str]:
        return self.client.keys(pattern)

    def flushall(self) -> bool:
        return self.client.flushall()

redis_client = RedisClient()
