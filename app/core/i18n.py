# backend/app/core/i18n.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict
import os
import json

_LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")
# load available translations into memory (json files: en.json, zh.json, fr.json, etc.)
_translations: Dict[str, Dict[str, str]] = {}
for fname in os.listdir(_LOCALE_DIR) if os.path.isdir(_LOCALE_DIR) else []:
    if fname.endswith(".json"):
        locale = fname.replace(".json", "")
        try:
            with open(os.path.join(_LOCALE_DIR, fname), "r", encoding="utf-8") as f:
                _translations[locale] = json.load(f)
        except Exception:
            _translations[locale] = {}

def detect_lang_from_header(accept_lang: str | None):
    if not accept_lang:
        return "en"
    parts = accept_lang.split(",")
    if not parts:
        return "en"
    lang = parts[0].split("-")[0]
    return lang if lang in _translations else "en"

def t(key: str, lang: str = "en"):
    return _translations.get(lang, {}).get(key, key)

class LocalizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Query param override: ?lang=xx
        lang = request.query_params.get("lang")
        if not lang:
            lang = detect_lang_from_header(request.headers.get("accept-language"))
        request.state.lang = lang
        response = await call_next(request)
        return response
