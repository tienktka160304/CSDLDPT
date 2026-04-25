from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import cv2

try:
    from skimage.feature import graycomatrix, graycoprops, local_binary_pattern, hog
except ImportError:  # older skimage spelling
    from skimage.feature import greycomatrix as graycomatrix
    from skimage.feature import greycoprops as graycoprops
    from skimage.feature import local_binary_pattern, hog


def _safe_stats(values: np.ndarray) -> tuple[float, float]:
    if values is None or len(values) == 0:
        return 0.0, 0.0
    values = np.asarray(values, dtype=np.float32)
    return float(np.mean(values)), float(np.std(values))


def _hist(channel: np.ndarray, bins: int = 32, value_range=(0, 256)) -> list[float]:
    h, _ = np.histogram(channel.reshape(-1), bins=bins, range=value_range)
    h = h.astype(np.float32)
    total = float(h.sum())
    if total > 0:
        h /= total
    return h.tolist()


def extract_features_from_image(image_path: str | Path, size: int = 224) -> dict:
    """Extract features compatible with the feature JSON produced in part 1."""
    image_path = Path(image_path)
    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Cannot read image: {image_path}")

    original_height, original_width = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_AREA)

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    item: dict[str, object] = {
        "filename": image_path.name,
        "filepath": str(image_path),
        "original_width": int(original_width),
        "original_height": int(original_height),
        "original_aspect": float(original_width / max(original_height, 1)),
        "channels": 3,
        "norm_width": size,
        "norm_height": size,
        "status": "success",
    }

    # Color histograms and summary statistics
    for idx, name in enumerate(["R", "G", "B"]):
        channel = rgb[:, :, idx]
        item[f"hist_rgb_{name}"] = _hist(channel, bins=32, value_range=(0, 256))
        item[f"color_mean_{name}"] = float(np.mean(channel))
        item[f"color_std_{name}"] = float(np.std(channel))

    for idx, name in enumerate(["H", "S", "V"]):
        channel = hsv[:, :, idx]
        max_val = 180 if name == "H" else 256
        item[f"hist_hsv_{name}"] = _hist(channel, bins=32, value_range=(0, max_val))
        item[f"color_mean_hsv_{name}"] = float(np.mean(channel))
    # Part 1 did not store HSV std, so we do not add it.

    # LBP histogram: P + 2 = 26 bins with method='uniform'
    P, R = 24, 3
    lbp = local_binary_pattern(gray, P=P, R=R, method="uniform")
    lbp_hist, _ = np.histogram(lbp.reshape(-1), bins=np.arange(0, P + 3), range=(0, P + 2))
    lbp_hist = lbp_hist.astype(np.float32)
    lbp_hist /= max(float(lbp_hist.sum()), 1.0)
    item["lbp_histogram"] = lbp_hist.tolist()

    # GLCM texture, quantized to 32 levels for speed and stability
    gray_q = np.floor(gray.astype(np.float32) / 8).astype(np.uint8)
    distances = [1, 3]
    angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
    angle_names = ["a0", "a45", "a90", "a135"]
    glcm = graycomatrix(gray_q, distances=distances, angles=angles, levels=32, symmetric=True, normed=True)
    for prop in ["contrast", "dissimilarity", "homogeneity", "energy", "correlation", "ASM"]:
        values = graycoprops(glcm, prop)
        flat_values = []
        for d_i, d in enumerate(distances):
            for a_i, a_name in enumerate(angle_names):
                val = float(values[d_i, a_i])
                item[f"glcm_{prop}_d{d}_{a_name}"] = val
                flat_values.append(val)
        item[f"glcm_{prop}_mean"] = float(np.mean(flat_values))
        item[f"glcm_{prop}_std"] = float(np.std(flat_values))

    # HOG shape feature
    hog_vector = hog(
        gray,
        orientations=9,
        pixels_per_cell=(8, 8),
        cells_per_block=(2, 2),
        block_norm="L2-Hys",
        feature_vector=True,
    ).astype(np.float32)
    item["hog_mean"] = float(np.mean(hog_vector))
    item["hog_std"] = float(np.std(hog_vector))
    item["hog_max"] = float(np.max(hog_vector)) if hog_vector.size else 0.0
    item["hog_energy"] = float(np.sum(hog_vector ** 2))
    item["hog_vector_100"] = np.pad(hog_vector[:100], (0, max(0, 100 - min(100, hog_vector.size))), mode="constant").tolist()
    item["hog_vector_length"] = int(hog_vector.size)

    # SIFT descriptors. If SIFT is missing, ORB is used and descriptor is padded to 128 dims.
    sift_desc = None
    keypoints = []
    try:
        sift = cv2.SIFT_create()
        keypoints, sift_desc = sift.detectAndCompute(gray, None)
    except Exception:
        orb = cv2.ORB_create(nfeatures=500)
        keypoints, sift_desc = orb.detectAndCompute(gray, None)

    if sift_desc is None or len(keypoints) == 0:
        item.update(
            {
                "sift_num_keypoints": 0,
                "sift_mean_response": 0.0,
                "sift_std_response": 0.0,
                "sift_mean_size": 0.0,
                "sift_mean_angle": 0.0,
                "sift_descriptor_mean": 0.0,
                "sift_descriptor_std": 0.0,
                "sift_avg_descriptor": [0.0] * 128,
            }
        )
    else:
        responses = np.asarray([kp.response for kp in keypoints], dtype=np.float32)
        sizes = np.asarray([kp.size for kp in keypoints], dtype=np.float32)
        angles_kp = np.asarray([kp.angle for kp in keypoints], dtype=np.float32)
        desc = np.asarray(sift_desc, dtype=np.float32)
        avg_desc = np.mean(desc, axis=0)
        if avg_desc.size < 128:
            avg_desc = np.pad(avg_desc, (0, 128 - avg_desc.size), mode="constant")
        elif avg_desc.size > 128:
            avg_desc = avg_desc[:128]

        item.update(
            {
                "sift_num_keypoints": int(len(keypoints)),
                "sift_mean_response": float(np.mean(responses)),
                "sift_std_response": float(np.std(responses)),
                "sift_mean_size": float(np.mean(sizes)),
                "sift_mean_angle": float(np.mean(angles_kp)),
                "sift_descriptor_mean": float(np.mean(desc)),
                "sift_descriptor_std": float(np.std(desc)),
                "sift_avg_descriptor": avg_desc.astype(np.float32).tolist(),
            }
        )

    # SURF is often unavailable in normal OpenCV builds; ORB fallback matches part 1 naming.
    orb = cv2.ORB_create(nfeatures=500)
    orb_kp, orb_desc = orb.detectAndCompute(gray, None)
    item["surf_method"] = "ORB_fallback"
    if orb_desc is None or len(orb_kp) == 0:
        item.update(
            {
                "surf_num_keypoints": 0,
                "surf_descriptor_mean": 0.0,
                "surf_descriptor_std": 0.0,
                "surf_mean_response": 0.0,
                "surf_mean_size": 0.0,
            }
        )
    else:
        orb_resp = np.asarray([kp.response for kp in orb_kp], dtype=np.float32)
        orb_sizes = np.asarray([kp.size for kp in orb_kp], dtype=np.float32)
        orb_desc = np.asarray(orb_desc, dtype=np.float32)
        item.update(
            {
                "surf_num_keypoints": int(len(orb_kp)),
                "surf_descriptor_mean": float(np.mean(orb_desc)),
                "surf_descriptor_std": float(np.std(orb_desc)),
                "surf_mean_response": float(np.mean(orb_resp)),
                "surf_mean_size": float(np.mean(orb_sizes)),
            }
        )

    return item
