# backend/app/core/i18n.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional
import os
import json

# Available languages worldwide (we'll support all major languages)
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ru': 'Russian',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'pt': 'Portuguese',
    'it': 'Italian',
    'nl': 'Dutch',
    'tr': 'Turkish',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'pl': 'Polish',
    'uk': 'Ukrainian',
    'ro': 'Romanian',
    'hu': 'Hungarian',
    'sv': 'Swedish',
    'da': 'Danish',
    'fi': 'Finnish',
    'no': 'Norwegian',
    'cs': 'Czech',
    'el': 'Greek',
    'he': 'Hebrew',
    'id': 'Indonesian',
    'ms': 'Malay',
    'fa': 'Persian',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'mr': 'Marathi',
    'ur': 'Urdu',
    'sw': 'Swahili'
}

_LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")
_translations: Dict[str, Dict[str, str]] = {}

# Load all translation files
for fname in os.listdir(_LOCALE_DIR) if os.path.isdir(_LOCALE_DIR) else []:
    if fname.endswith(".json"):
        locale = fname.replace(".json", "")
        try:
            with open(os.path.join(_LOCALE_DIR, fname), "r", encoding="utf-8") as f:
                _translations[locale] = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load locale {locale}: {e}")
            _translations[locale] = {}

def detect_language_from_ip(ip_address: str) -> str:
    """Detect language based on IP address geolocation"""
    try:
        # Try to import the geolocation library
        from ip2geotools.databases.noncommercial import DbIpCity
        import pycountry
        
        if ip_address and ip_address != "127.0.0.1":
            response = DbIpCity.get(ip_address, api_key='free')
            country_code = response.country
            country = pycountry.countries.get(alpha_2=country_code)
            
            if country:
                # Map country to primary language
                country_language_map = {
                    'US': 'en', 'GB': 'en', 'CA': 'en', 'AU': 'en', 'NZ': 'en',
                    'ES': 'es', 'MX': 'es', 'AR': 'es', 'CO': 'es', 'PE': 'es',
                    'FR': 'fr', 'BE': 'fr', 'CH': 'fr',
                    'DE': 'de', 'AT': 'de', 'CH': 'de',
                    'CN': 'zh', 'TW': 'zh', 'SG': 'zh', 'HK': 'zh',
                    'JP': 'ja', 'KR': 'ko', 'RU': 'ru',
                    'SA': 'ar', 'AE': 'ar', 'EG': 'ar', 'MA': 'ar',
                    'IN': 'hi', 'BR': 'pt', 'PT': 'pt',
                    'IT': 'it', 'NL': 'nl', 'TR': 'tr',
                    'VN': 'vi', 'TH': 'th', 'PL': 'pl',
                    'UA': 'uk', 'RO': 'ro', 'HU': 'hu',
                    'SE': 'sv', 'DK': 'da', 'FI': 'fi',
                    'NO': 'no', 'CZ': 'cs', 'GR': 'el',
                    'IL': 'he', 'ID': 'id', 'MY': 'ms',
                    'IR': 'fa', 'BD': 'bn', 'LK': 'ta',
                    'PK': 'ur', 'KE': 'sw', 'TZ': 'sw'
                }
                
                return country_language_map.get(country_code, 'en')
    except ImportError:
        print("⚠️ ip2geotools or pycountry not installed. Using fallback detection.")
    except Exception as e:
        print(f"⚠️ IP language detection failed: {e}")
    
    return 'en'

def detect_language_from_header(accept_lang: Optional[str]) -> str:
    """Detect language from browser Accept-Language header"""
    if not accept_lang:
        return "en"
    
    try:
        languages = accept_lang.split(",")
        for lang in languages:
            lang_code = lang.split(";")[0].split("-")[0].strip()
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code
    except Exception as e:
        print(f"⚠️ Header language detection failed: {e}")
    
    return "en"

def get_user_language_preference(user_lang: Optional[str]) -> str:
    """Get user's saved language preference"""
    if user_lang and user_lang in SUPPORTED_LANGUAGES:
        return user_lang
    return "en"

def t(key: str, lang: str = "en", **kwargs) -> str:
    """Translation function with fallback and variable substitution"""
    translation = _translations.get(lang, {}).get(key, _translations.get('en', {}).get(key, key))
    
    # Replace variables in translation
    if kwargs:
        try:
            translation = translation.format(**kwargs)
        except KeyError:
            pass  # Keep original if formatting fails
    
    return translation

def get_supported_languages() -> Dict[str, str]:
    """Get all supported languages with their display names"""
    return SUPPORTED_LANGUAGES

class AdvancedLocalizationMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware with IP detection, browser detection, and user preference"""
    
    async def dispatch(self, request: Request, call_next):
        # 1. Query parameter has highest priority (?lang=en)
        lang = request.query_params.get("lang")
        
        # 2. Check for user preference in header (for authenticated requests)
        if not lang and hasattr(request.state, 'user'):
            user_lang = getattr(request.state.user, 'language_preference', None)
            if user_lang:
                lang = user_lang
        
        # 3. Browser Accept-Language header
        if not lang:
            accept_lang = request.headers.get("accept-language")
            lang = detect_language_from_header(accept_lang)
        
        # 4. IP-based geolocation (fallback)
        if not lang or lang not in SUPPORTED_LANGUAGES:
            client_ip = request.client.host if request.client else "127.0.0.1"
            lang = detect_language_from_ip(client_ip)
        
        # Final fallback to English
        if lang not in SUPPORTED_LANGUAGES:
            lang = "en"
        
        # Set language in request state
        request.state.lang = lang
        request.state.supported_languages = SUPPORTED_LANGUAGES
        
        response = await call_next(request)
        
        # Add language header to response
        response.headers["Content-Language"] = lang
        
        return response