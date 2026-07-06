import json
import os
from pathlib import Path

import click

DATA_FILENAME = "books.json"


def get_data_dir() -> Path:
    override = os.environ.get("APP_CLI_DATA_DIR")
    if override:
        return Path(override)
    return Path(click.get_app_dir("app-cli"))


def get_data_path() -> Path:
    return get_data_dir() / DATA_FILENAME


def load_data() -> dict:
    path = get_data_path()
    if not path.exists():
        return {"books": [], "finna_cache": {}}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("books", [])
    data.setdefault("finna_cache", {})
    return data


def save_data(data: dict) -> None:
    path = get_data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
