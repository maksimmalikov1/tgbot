"""Пакет данных: загрузка услуг из services.json (единый источник с сайтом)."""
import json

from config import SERVICES_PATH

_services_cache = None


def load_services(force: bool = False):
    """Возвращает список услуг (list[dict]) из services.json. Кэшируется."""
    global _services_cache
    if _services_cache is None or force:
        with open(SERVICES_PATH, "r", encoding="utf-8") as f:
            _services_cache = json.load(f)
    return _services_cache


def get_service(service_id: str):
    """Возвращает услугу по id или None."""
    for service in load_services():
        if service.get("id") == service_id:
            return service
    return None
