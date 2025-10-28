import redis
import json
import os
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_client = None
        self.connect()

    def connect(self):
        try:
            # Use environment variable first, then fallback to settings
            redis_url = os.getenv('REDIS_URL', getattr(settings, 'REDIS_URL', 'redis://localhost:6379'))
            
            if redis_url.startswith('redis://'):
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    max_connections=20
                )
            else:
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    max_connections=20
                )
            
            self.redis_client.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None

    def get_client(self):
        if self.redis_client is None:
            self.connect()
        return self.redis_client

    def cache_get(self, key: str):
        try:
            client = self.get_client()
            if client:
                value = client.get(key)
                return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None

    def cache_set(self, key: str, value, expire: int = 3600):
        try:
            client = self.get_client()
            if client:
                client.setex(key, expire, json.dumps(value))
                return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
        return False

    def delete_key(self, key: str):
        try:
            client = self.get_client()
            if client:
                client.delete(key)
                return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
        return False

    def health_check(self):
        try:
            client = self.get_client()
            if client and client.ping():
                return True
        except:
            pass
        return False

redis_client = RedisClient()
