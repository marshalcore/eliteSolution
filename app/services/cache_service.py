from app.core.redis import redis_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheService:
    @staticmethod
    def cache_otp(phone: str, otp: str, purpose: str):
        key = f"otp:{purpose}:{phone}"
        return redis_client.cache_set(key, {"otp": otp}, settings.CACHE_TTL_OTP)

    @staticmethod
    def get_otp(phone: str, purpose: str):
        key = f"otp:{purpose}:{phone}"
        return redis_client.cache_get(key)

    @staticmethod
    def delete_otp(phone: str, purpose: str):
        key = f"otp:{purpose}:{phone}"
        return redis_client.delete_key(key)

    @staticmethod
    def cache_user_session(user_id: int, session_data: dict):
        key = f"user_session:{user_id}"
        return redis_client.cache_set(key, session_data, settings.CACHE_TTL_USER)

    @staticmethod
    def get_user_session(user_id: int):
        key = f"user_session:{user_id}"
        return redis_client.cache_get(key)

    @staticmethod
    def delete_user_session(user_id: int):
        key = f"user_session:{user_id}"
        return redis_client.delete_key(key)

cache_service = CacheService()
