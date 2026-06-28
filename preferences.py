import json
from pathlib import Path
from typing import List

DEFAULT_VISIBLE_COLUMNS = ["Projeto", "Descrição", "Início", "Fim", "Duração"]
PREFERENCES_FILE = Path(__file__).resolve().parent / "preferences.json"


def load_visible_columns(path: Path | None = None) -> List[str]:
    preferences_path = path or PREFERENCES_FILE
    if not preferences_path.exists():
        return list(DEFAULT_VISIBLE_COLUMNS)

    try:
        with preferences_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                return data
    except (json.JSONDecodeError, OSError):
        pass

    return list(DEFAULT_VISIBLE_COLUMNS)


def save_visible_columns(columns: List[str], path: Path | None = None) -> None:
    preferences_path = path or PREFERENCES_FILE
    with preferences_path.open("w", encoding="utf-8") as handle:
        json.dump(columns, handle, ensure_ascii=False, indent=2)
