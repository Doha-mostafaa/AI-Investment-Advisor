import redis
import json
from loguru import logger
from ingestion.config import config

client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=3,
)

def set_json(key: str, value: dict, ttl_seconds: int = None):
    client.set(key, json.dumps(value, default=str), ex=ttl_seconds)

def get_json(key: str):
    raw = client.get(key)
    return json.loads(raw) if raw else None

def delete(key: str):
    client.delete(key)

def healthcheck() -> bool:
    try:
        return client.ping()
    except Exception as e:
        logger.error(f"Redis healthcheck failed: {e}")
        return False