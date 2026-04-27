from __future__ import annotations

from pathlib import Path
import numpy as np
import cv2

try:
    from skimage.feature import graycomatrix, graycoprops, local_binary_pattern, hog
except ImportError:
    from skimage.feature import greycomatrix as graycomatrix
    from skimage.feature import greycoprops as graycoprops
    from skimage.feature import local_binary_pattern, hog


def _hist(channel: np.ndarray, bins: int = 32, value_range=(0, 256)) -> list[float]:
    hist, _ = np.histogram(channel.reshape(-1), bins=bins, range=value_range)
    hist = hist.astype(np.float32)

    total = float(hist.sum())
    if total > 0:
        hist /= total

    return hist.tolist()


def _zero_sift_features() -> dict:
    return {
        "sift_num_keypoints": 0,
        "sift_mean_response": 0.0,
        "sift_std_response": 0.0,
        "sift_mean_size": 0.0,
        "sift_mean_angle": 0.0,
        "sift_descriptor_mean": 0.0,
        "sift_descriptor_std": 0.0,
        "sift_avg_descriptor": [0.0] * 128,
    }


def _zero_orb_features() -> dict:
    return {
        "surf_method": "ORB_fallback",
        "surf_num_keypoints": 0,
        "surf_descriptor_mean": 0.0,
        "surf_descriptor_std": 0.0,
        "surf_mean_response": 0.0,
        "surf_mean_size": 0.0,
    }


def extract_features_from_image(image_path: str | Path, size: int = 224) -> dict:
    """
    Extract feature cho ảnh upload mới.

    File này được chỉnh để khớp pipeline trích xuất đặc trưng của phần 1:
    Color: RGB/HSV histogram + mean/std
    Texture: LBP + GLCM
    Shape: HOG + SIFT + ORB fallback
    """

    image_path = Path(image_path)

    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Cannot read image: {image_path}")

    original_height, original_width = bgr.shape[:2]

    # Resize giống phần 1: 224x224, dùng INTER_AREA
    bgr_resized = cv2.resize(bgr, (size, size), interpolation=cv2.INTER_AREA)

    rgb = cv2.cvtColor(bgr_resized, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(bgr_resized, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(bgr_resized, cv2.COLOR_BGR2GRAY)

    item: dict[str, object] = {
        "filename": image_path.name,
        "filepath": str(image_path),
        "status": "success",
        "original_width": int(original_width),
        "original_height": int(original_height),
        "original_aspect": float(original_width / max(original_height, 1)),
        "channels": 3,
        "norm_width": size,
        "norm_height": size,
    }

    # =========================================================
    # 1. COLOR FEATURES
    # =========================================================

    for idx, name in enumerate(["R", "G", "B"]):
        channel = rgb[:, :, idx]

        item[f"hist_rgb_{name}"] = _hist(
            channel,
            bins=32,
            value_range=(0, 256),
        )

        item[f"color_mean_{name}"] = float(np.mean(channel))
        item[f"color_std_{name}"] = float(np.std(channel))

    for idx, name in enumerate(["H", "S", "V"]):
        channel = hsv[:, :, idx]

        # OpenCV HSV: H nằm trong [0, 180), S/V nằm trong [0, 256)
        value_range = (0, 180) if name == "H" else (0, 256)

        item[f"hist_hsv_{name}"] = _hist(
            channel,
            bins=32,
            value_range=value_range,
        )

        item[f"color_mean_hsv_{name}"] = float(np.mean(channel))

    # =========================================================
    # 2. LBP TEXTURE FEATURES
    # =========================================================

    radius = 3
    points = 8 * radius

    lbp = local_binary_pattern(
        gray,
        P=points,
        R=radius,
        method="uniform",
    )

    # Uniform LBP có P + 2 bins = 26 bins
    lbp_hist, _ = np.histogram(
        lbp.reshape(-1),
        bins=np.arange(0, points + 3),
        range=(0, points + 2),
    )

    lbp_hist = lbp_hist.astype(np.float32)
    lbp_hist /= max(float(lbp_hist.sum()), 1.0)

    item["lbp_histogram"] = lbp_hist.tolist()

    # =========================================================
    # 3. GLCM TEXTURE FEATURES
    # =========================================================

    # Phần 1 dùng gray levels = 64
    # Ảnh xám 0..255 lượng tử về 0..63 bằng chia 4
    gray_q = np.floor(gray.astype(np.float32) / 4).astype(np.uint8)

    distances = [1, 3]
    angles = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
    angle_names = ["a0", "a45", "a90", "a135"]

    glcm = graycomatrix(
        gray_q,
        distances=distances,
        angles=angles,
        levels=64,
        symmetric=True,
        normed=True,
    )

    glcm_props = [
        "contrast",
        "dissimilarity",
        "homogeneity",
        "energy",
        "correlation",
        "ASM",
    ]

    for prop in glcm_props:
        values = graycoprops(glcm, prop)

        flat_values = []

        for d_i, d in enumerate(distances):
            for a_i, a_name in enumerate(angle_names):
                value = float(values[d_i, a_i])
                item[f"glcm_{prop}_d{d}_{a_name}"] = value
                flat_values.append(value)

        item[f"glcm_{prop}_mean"] = float(np.mean(flat_values))
        item[f"glcm_{prop}_std"] = float(np.std(flat_values))

    # =========================================================
    # 4. HOG SHAPE FEATURES
    # =========================================================

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
    item["hog_vector_length"] = int(hog_vector.size)

    # Giữ 100 giá trị đầu giống format JSON đang dùng
    hog_100 = hog_vector[:100]
    if hog_100.size < 100:
        hog_100 = np.pad(hog_100, (0, 100 - hog_100.size), mode="constant")

    item["hog_vector_100"] = hog_100.tolist()

    # =========================================================
    # 5. SIFT SHAPE FEATURES
    # =========================================================

    try:
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(gray, None)
    except Exception:
        keypoints, descriptors = [], None

    if descriptors is None or len(keypoints) == 0:
        item.update(_zero_sift_features())
    else:
        # Phần 1 lấy top 50 keypoints mạnh nhất theo response
        sorted_indices = sorted(
            range(len(keypoints)),
            key=lambda i: keypoints[i].response,
            reverse=True,
        )[:50]

        keypoints_top = [keypoints[i] for i in sorted_indices]
        descriptors_top = descriptors[sorted_indices].astype(np.float32)

        responses = np.asarray([kp.response for kp in keypoints_top], dtype=np.float32)
        sizes = np.asarray([kp.size for kp in keypoints_top], dtype=np.float32)
        angles_kp = np.asarray([kp.angle for kp in keypoints_top], dtype=np.float32)

        avg_descriptor = np.mean(descriptors_top, axis=0)

        if avg_descriptor.size < 128:
            avg_descriptor = np.pad(avg_descriptor, (0, 128 - avg_descriptor.size), mode="constant")
        elif avg_descriptor.size > 128:
            avg_descriptor = avg_descriptor[:128]

        item["sift_num_keypoints"] = int(len(keypoints_top))
        item["sift_mean_response"] = float(np.mean(responses))
        item["sift_std_response"] = float(np.std(responses))
        item["sift_mean_size"] = float(np.mean(sizes))
        item["sift_mean_angle"] = float(np.mean(angles_kp))
        item["sift_descriptor_mean"] = float(np.mean(descriptors_top))
        item["sift_descriptor_std"] = float(np.std(descriptors_top))
        item["sift_avg_descriptor"] = avg_descriptor.astype(np.float32).tolist()

    # =========================================================
    # 6. SURF / ORB FALLBACK FEATURES
    # =========================================================

    # Theo phần 1: SURF thường không có do patent, dùng ORB fallback
    orb = cv2.ORB_create(nfeatures=500)
    orb_keypoints, orb_descriptors = orb.detectAndCompute(gray, None)

    if orb_descriptors is None or len(orb_keypoints) == 0:
        item.update(_zero_orb_features())
    else:
        orb_responses = np.asarray([kp.response for kp in orb_keypoints], dtype=np.float32)
        orb_sizes = np.asarray([kp.size for kp in orb_keypoints], dtype=np.float32)
        orb_descriptors = orb_descriptors.astype(np.float32)

        item["surf_method"] = "ORB_fallback"
        item["surf_num_keypoints"] = int(len(orb_keypoints))
        item["surf_descriptor_mean"] = float(np.mean(orb_descriptors))
        item["surf_descriptor_std"] = float(np.std(orb_descriptors))
        item["surf_mean_response"] = float(np.mean(orb_responses))
        item["surf_mean_size"] = float(np.mean(orb_sizes))

    return item