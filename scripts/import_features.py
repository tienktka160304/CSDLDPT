from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.feature_vector import build_vector_spec, flatten_features, standardize_and_normalize, dumps_json
from app.database import array_to_blob


def run_schema(conn: sqlite3.Connection) -> None:
    schema = PROJECT_ROOT / "sql" / "schema_sqlite.sql"
    conn.executescript(schema.read_text(encoding="utf-8"))
    conn.commit()


def import_features(json_path: Path, images_dir: Path, db_path: Path) -> None:
    with json_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    records = [r for r in records if r.get("status") == "success"]
    if not records:
        raise ValueError("Không có record status=success trong file JSON.")

    vector_spec = build_vector_spec(records[0])
    raw_vectors = np.vstack([flatten_features(r, vector_spec) for r in records]).astype(np.float32)

    mean = raw_vectors.mean(axis=0).astype(np.float32)
    std = raw_vectors.std(axis=0).astype(np.float32)
    std[std == 0] = 1.0

    norm_vectors = np.vstack([standardize_and_normalize(v, mean, std) for v in raw_vectors]).astype(np.float32)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    run_schema(conn)

    for idx, (record, raw_vec, norm_vec) in enumerate(zip(records, raw_vectors, norm_vectors), start=1):
        filename = record["filename"]
        stored_path = filename if (images_dir / filename).exists() else str(Path("normalized_images") / filename)

        cur = conn.execute(
            """
            INSERT INTO images(
                filename, original_path, stored_path,
                original_width, original_height, original_aspect, channels, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                record.get("filepath"),
                stored_path,
                record.get("original_width"),
                record.get("original_height"),
                record.get("original_aspect"),
                record.get("channels"),
                record.get("status", "success"),
            ),
        )
        image_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO feature_vectors(image_id, vector_dim, raw_vector, norm_vector, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                image_id,
                int(raw_vec.shape[0]),
                array_to_blob(raw_vec),
                array_to_blob(norm_vec),
                dumps_json(record),
            ),
        )

    metadata = {
        "vector_spec": vector_spec,
        "mean": mean.astype(float).tolist(),
        "std": std.astype(float).tolist(),
        "feature_groups": {
            "color": "RGB/HSV histogram + color mean/std",
            "texture": "LBP + GLCM",
            "shape": "HOG + SIFT/ORB/SURF fallback statistics",
            "similarity": "standardize features -> L2 normalize -> cosine similarity",
        },
        "total_images": len(records),
        "vector_dim": int(raw_vectors.shape[1]),
    }
    for key, value in metadata.items():
        conn.execute(
            "INSERT INTO vector_metadata(key, value) VALUES (?, ?)",
            (key, dumps_json(value)),
        )

    conn.commit()
    conn.close()

    print(f"Imported {len(records)} images")
    print(f"Vector dimension: {raw_vectors.shape[1]}")
    print(f"Database: {db_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, type=Path, help="Path to features_output.json from part 1")
    parser.add_argument("--images-dir", required=True, type=Path, help="Path to normalized_images folder")
    parser.add_argument("--db", default=PROJECT_ROOT / "data" / "image_search.db", type=Path)
    args = parser.parse_args()

    import_features(args.json, args.images_dir, args.db)


if __name__ == "__main__":
    main()
