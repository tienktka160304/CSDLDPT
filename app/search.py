from __future__ import annotations

import sqlite3
import numpy as np
from .database import blob_to_array, get_metadata
from .feature_vector import flatten_features, standardize_and_normalize


class ImageSearchEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.vector_spec = get_metadata(conn, "vector_spec")
        self.mean = np.asarray(get_metadata(conn, "mean"), dtype=np.float32)
        self.std = np.asarray(get_metadata(conn, "std"), dtype=np.float32)
        self._load_vectors()

    def _load_vectors(self) -> None:
        rows = self.conn.execute(
            """
            SELECT i.id, i.filename, i.stored_path, fv.norm_vector
            FROM images i
            JOIN feature_vectors fv ON i.id = fv.image_id
            WHERE i.status = 'success'
            ORDER BY i.id
            """
        ).fetchall()

        self.ids: list[int] = []
        self.filenames: list[str] = []
        self.stored_paths: list[str] = []
        vectors: list[np.ndarray] = []

        for row in rows:
            self.ids.append(int(row["id"]))
            self.filenames.append(str(row["filename"]))
            self.stored_paths.append(str(row["stored_path"]))
            vectors.append(blob_to_array(row["norm_vector"]))

        self.matrix = np.vstack(vectors).astype(np.float32) if vectors else np.empty((0, 0), dtype=np.float32)

    @property
    def count(self) -> int:
        return len(self.ids)

    @property
    def dim(self) -> int:
        return int(self.matrix.shape[1]) if self.matrix.ndim == 2 and self.matrix.size else 0

    def vector_from_filename(self, filename: str) -> np.ndarray:
        row = self.conn.execute(
            """
            SELECT fv.norm_vector
            FROM images i
            JOIN feature_vectors fv ON i.id = fv.image_id
            WHERE i.filename = ?
            """,
            (filename,),
        ).fetchone()
        if row is None:
            raise FileNotFoundError(filename)
        return blob_to_array(row["norm_vector"]).astype(np.float32)

    def vector_from_features(self, features: dict) -> np.ndarray:
        raw = flatten_features(features, self.vector_spec)
        return standardize_and_normalize(raw, self.mean, self.std)

    def search_vector(self, query_vector: np.ndarray, top_k: int = 5, exclude_filename: str | None = None) -> list[dict]:
        if self.count == 0:
            return []

        top_k = max(1, min(int(top_k), self.count))
        sims = self.matrix @ query_vector.astype(np.float32)

        if exclude_filename is not None:
            for idx, name in enumerate(self.filenames):
                if name == exclude_filename:
                    sims[idx] = -np.inf
                    break

        # Get a little more than needed, then sort exactly.
        candidate_count = min(top_k + 5, len(sims))
        idxs = np.argpartition(-sims, candidate_count - 1)[:candidate_count]
        idxs = idxs[np.argsort(-sims[idxs])][:top_k]

        results: list[dict] = []
        for rank, idx in enumerate(idxs, start=1):
            sim = float(sims[idx])
            if not np.isfinite(sim):
                continue
            results.append(
                {
                    "rank": rank,
                    "id": self.ids[idx],
                    "filename": self.filenames[idx],
                    "stored_path": self.stored_paths[idx],
                    "similarity": round(sim, 6),
                    "distance": round(1.0 - sim, 6),
                    "image_url": f"/images/{self.filenames[idx]}",
                }
            )
        return results
