from __future__ import annotations

from pathlib import Path
import os
import sqlite3
import json
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "image_search.db"
DEFAULT_IMAGES_DIR = PROJECT_ROOT / "data" / "normalized_images"


def get_db_path() -> Path:
    return Path(os.getenv("DB_PATH", str(DEFAULT_DB_PATH))).resolve()


def get_images_dir() -> Path:
    return Path(os.getenv("IMAGES_DIR", str(DEFAULT_IMAGES_DIR))).resolve()


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    db = Path(db_path) if db_path else get_db_path()
    conn = sqlite3.connect(str(db), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def array_to_blob(arr: np.ndarray) -> bytes:
    return np.asarray(arr, dtype=np.float32).tobytes()


def blob_to_array(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def get_metadata(conn: sqlite3.Connection, key: str):
    row = conn.execute("SELECT value FROM vector_metadata WHERE key = ?", (key,)).fetchone()
    if row is None:
        raise KeyError(f"Missing metadata key: {key}")
    return json.loads(row["value"])
