"""
Единый источник информации о сервисах.
Все скрипты импортируют отсюда.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List

_REGISTRY = None
_REGISTRY_PATH = Path(__file__).parent.parent / "service-registry.yml"


def load_registry() -> Dict[str, Any]:
    """Загружает service-registry.yaml"""
    global _REGISTRY
    if _REGISTRY is None:
        if not _REGISTRY_PATH.exists():
            raise FileNotFoundError(f"Service registry not found: {_REGISTRY_PATH}")
        with open(_REGISTRY_PATH) as f:
            _REGISTRY = yaml.safe_load(f)
    return _REGISTRY


def get_services() -> List[str]:
    """Возвращает список имен сервисов в порядке объявления"""
    registry = load_registry()
    return list(registry["services"].keys())


def get_service_config(service: str) -> Dict[str, Any]:
    """Возвращает конфиг конкретного сервиса"""
    registry = load_registry()
    return registry["services"].get(service, {})


def get_strategy(service: str) -> str:
    """Возвращает стратегию деплоя (blue-green или single)"""
    return get_service_config(service).get("strategy", "single")


def is_blue_green(service: str) -> bool:
    """Проверяет, использует ли сервис blue-green стратегию"""
    return get_strategy(service) == "blue-green"


def is_single(service: str) -> bool:
    """Проверяет, использует ли сервис single стратегию"""
    return get_strategy(service) == "single"


def get_blue_green_services() -> List[str]:
    """Возвращает список blue-green сервисов"""
    registry = load_registry()
    return [
        service
        for service, config in registry["services"].items()
        if config.get("strategy") == "blue-green"
    ]


def get_service_containers(service: str) -> List[str]:
    """
    Возвращает имена контейнеров для сервиса.
    Для blue-green: ['gateway-blue', 'gateway-green']
    Для single: ['nginx']
    """
    config = get_service_config(service)
    if config.get("strategy") == "blue-green":
        return [f"{service}-blue", f"{service}-green"]
    return [service]


# Для обратной совместимости с существующими скриптами
SERVICES = get_services()
