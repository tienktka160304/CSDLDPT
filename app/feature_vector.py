from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import numpy as np


EXCLUDE_KEYS = {
    "filename",
    "filepath",
    "status",
    "surf_method",
    "original_width",
    "original_height",
    "original_aspect",
    "channels",
    "norm_width",
    "norm_height",
    "hog_vector_length",
}


@dataclass(frozen=True)
class VectorField:
    key: str
    length: int


def build_vector_spec(sample: dict[str, Any]) -> list[dict[str, int | str]]:
    """Create a deterministic vector specification from one JSON feature record."""
    spec: list[dict[str, int | str]] = []

    # Keep the order stable and interpretable: color -> texture -> shape/keypoint.
    preferred_prefixes = [
        "hist_rgb_",
        "hist_hsv_",
        "color_",
        "lbp_",
        "glcm_",
        "hog_",
        "sift_",
        "surf_",
    ]

    keys: list[str] = []
    for prefix in preferred_prefixes:
        keys.extend([k for k in sample.keys() if k.startswith(prefix)])
    keys.extend([k for k in sample.keys() if k not in keys])

    for key in keys:
        if key in EXCLUDE_KEYS:
            continue
        value = sample.get(key)
        if isinstance(value, list):
            spec.append({"key": key, "length": len(value)})
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            spec.append({"key": key, "length": 1})

    return spec


def flatten_features(item: dict[str, Any], vector_spec: list[dict[str, int | str]]) -> np.ndarray:
    """Flatten JSON features to a numeric vector following vector_spec."""
    values: list[float] = []

    for field in vector_spec:
        key = str(field["key"])
        expected_len = int(field["length"])
        value = item.get(key)

        if value is None:
            values.extend([0.0] * expected_len)
            continue

        if isinstance(value, list):
            arr = np.asarray(value, dtype=np.float32).reshape(-1)
            if arr.size < expected_len:
                arr = np.pad(arr, (0, expected_len - arr.size), mode="constant")
            elif arr.size > expected_len:
                arr = arr[:expected_len]
            values.extend(arr.astype(float).tolist())
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
        else:
            values.extend([0.0] * expected_len)

    out = np.asarray(values, dtype=np.float32)
    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    return out


def standardize_and_normalize(
    raw_vector: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
) -> np.ndarray:
    x = (raw_vector.astype(np.float32) - mean.astype(np.float32)) / std.astype(np.float32)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    norm = float(np.linalg.norm(x))
    if norm == 0.0:
        return x.astype(np.float32)
    return (x / norm).astype(np.float32)


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads_json(value: str) -> Any:
    return json.loads(value)
