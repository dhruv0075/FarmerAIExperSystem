"""Small file-backed translation helpers for the Flask/Jinja application."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple


LOCALE_DIRECTORY = Path(__file__).resolve().parents[1] / "locales"
SUPPORTED_LANGUAGES = {
    "en": "English",
    "mr": "मराठी",
    "hi": "हिन्दी",
}
DEFAULT_LANGUAGE = "en"


_RESOURCE_CACHE: Dict[str, Tuple[int, int, Dict[str, Any]]] = {}


def _load_resource(language: str) -> Dict[str, Any]:
    resource_path = LOCALE_DIRECTORY / f"{language}.json"
    metadata = resource_path.stat()
    cached = _RESOURCE_CACHE.get(language)
    if cached and cached[:2] == (metadata.st_mtime_ns, metadata.st_size):
        return cached[2]

    with resource_path.open(encoding="utf-8") as resource_file:
        resource = json.load(resource_file)
    if not isinstance(resource, dict):
        raise ValueError(f"Translation resource for {language} must be a JSON object.")
    _RESOURCE_CACHE[language] = (
        metadata.st_mtime_ns,
        metadata.st_size,
        resource,
    )
    return resource


def is_supported_language(language: Any) -> bool:
    return isinstance(language, str) and language in SUPPORTED_LANGUAGES


def _lookup(resource: Dict[str, Any], key: str) -> Any:
    value: Any = resource
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def translate(language: Any, key: str, **values: Any) -> str:
    selected_language = language if is_supported_language(language) else DEFAULT_LANGUAGE
    value = _lookup(_load_resource(selected_language), key)
    if not isinstance(value, str):
        value = _lookup(_load_resource(DEFAULT_LANGUAGE), key)
    if not isinstance(value, str):
        return key
    return value.format(**values) if values else value
