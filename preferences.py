import json
from pathlib import Path
from typing import List

KNOWN_COLUMNS = ["Data", "Início", "Fim", "Projeto", "Descrição", "Duração"]
DEFAULT_VISIBLE_COLUMNS = ["Data", "Início", "Fim", "Projeto", "Descrição", "Duração"]
PREFERENCES_FILE = Path(__file__).resolve().parent / "preferences.json"
TAGS_FILE = Path(__file__).resolve().parent / "tags.json"


def load_visible_columns(path: Path | None = None) -> List[str]:
    preferences_path = path or PREFERENCES_FILE
    if not preferences_path.exists():
        return list(DEFAULT_VISIBLE_COLUMNS)

    try:
        with preferences_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                normalized = []
                for column in DEFAULT_VISIBLE_COLUMNS:
                    if column in data:
                        normalized.append(column)
                for column in KNOWN_COLUMNS:
                    if column in data and column not in normalized:
                        normalized.append(column)
                return normalized or list(DEFAULT_VISIBLE_COLUMNS)
    except (json.JSONDecodeError, OSError):
        pass

    return list(DEFAULT_VISIBLE_COLUMNS)


def save_visible_columns(columns: List[str], path: Path | None = None) -> None:
    preferences_path = path or PREFERENCES_FILE
    valid_columns = [column for column in columns if column in KNOWN_COLUMNS]
    if not valid_columns:
        valid_columns = list(DEFAULT_VISIBLE_COLUMNS)
    with preferences_path.open("w", encoding="utf-8") as handle:
        json.dump(valid_columns, handle, ensure_ascii=False, indent=2)


def load_tags(path: Path | None = None) -> List[str]:
    tags_path = path or TAGS_FILE
    if not tags_path.exists():
        return []

    try:
        with tags_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                return data
    except (json.JSONDecodeError, OSError):
        pass

    return []


def save_tags(tags: List[str], path: Path | None = None) -> None:
    tags_path = path or TAGS_FILE
    normalized = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        value = tag.strip()
        if value and value not in normalized:
            normalized.append(value)
    with tags_path.open("w", encoding="utf-8") as handle:
        json.dump(normalized, handle, ensure_ascii=False, indent=2)
