import os
import sys
import cv2
import numpy as np

import DetectPlates
import DetectChars


def _clean_ground_truth(s: str) -> str:
    # Normalize to labels compatible với current KNN training.
    # Hiện tại DetectChars dự đoán bằng chr(ord_code) nên label trong classifications.txt là ASCII code.
    # Chỉ giữ A-Z và 0-9, loại bỏ '-', '.', khoảng trắng.
    s = s.upper()
    return "".join(ch for ch in s if ("0" <= ch <= "9") or ("A" <= ch <= "Z"))



def _append_sample(char_img_20x30: np.ndarray, label_char: str, *, classifications_path: str, flattened_images_path: str):
    # char_img_20x30 is expected to be grayscale binary-ish, shape (30,20)
    img = cv2.resize(char_img_20x30, (20, 30), interpolation=cv2.INTER_NEAREST)
    vec = img.reshape((1, 20 * 30)).astype(np.float32)
    # Ensure there is exactly the same dtype/shape as DetectChars expects
    # (DetectChars passes 1x(20*30) float32 to KNN)


    # Write label as ASCII code (to match existing pipeline)
    ascii_code = np.float32(ord(label_char))

    with open(flattened_images_path, "a", encoding="utf-8") as f_img:
        # flattened_images is one long text file with values separated by spaces/newlines.
        # The original generator writes one vector per line (whitespace separated). We'll do the same.
        f_img.write(" ".join(str(x) for x in vec.flatten().tolist()) + "\n")

    with open(classifications_path, "a", encoding="utf-8") as f_lab:
        f_lab.write(str(ascii_code) + "\n")


def _extract_char_rois_from_detected_plate(plate, show=False):
    # Re-run the same preprocessing steps as DetectChars.detectCharsInPlates,
    # but we return the per-char ROIs in left-to-right order.
    # This keeps behavior consistent with training.
    plate.imgGrayscale, plate.imgThresh = (None, None)

    plate.imgGrayscale, plate.imgThresh = __import__("Preprocess").preprocess(plate.imgPlate)

    # Resize + threshold again (same as DetectChars)
    plate.imgThresh = cv2.resize(plate.imgThresh, (0, 0), fx=1.6, fy=1.6)
    _, plate.imgThresh = cv2.threshold(
        plate.imgThresh, 0.0, 255.0, cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )

    listOfPossibleCharsInPlate = DetectChars.findPossibleCharsInPlate(plate.imgGrayscale, plate.imgThresh)
    listOfListsOfMatchingCharsInPlate = DetectChars.findListOfListsOfMatchingChars(listOfPossibleCharsInPlate)

    if len(listOfListsOfMatchingCharsInPlate) == 0:
        return []

    for i in range(0, len(listOfListsOfMatchingCharsInPlate)):
        listOfListsOfMatchingCharsInPlate[i].sort(key=lambda ch: ch.intCenterX)
        listOfListsOfMatchingCharsInPlate[i] = DetectChars.removeInnerOverlappingChars(listOfListsOfMatchingCharsInPlate[i])

    # Choose longest group
    longest = max(listOfListsOfMatchingCharsInPlate, key=lambda g: len(g))
    longest.sort(key=lambda ch: ch.intCenterX)

    rois = []
    for ch in longest:
        x, y, w, h = ch.intBoundingRectX, ch.intBoundingRectY, ch.intBoundingRectWidth, ch.intBoundingRectHeight
        roi = plate.imgThresh[y : y + h, x : x + w]
        roi_resized = cv2.resize(roi, (20, 30), interpolation=cv2.INTER_NEAREST)
        rois.append(roi_resized)

    return rois


def run(image_path: str, ground_truth: str, *, limit_to_first_n: int | None = None):
    classifications_path = "classifications.txt"
    flattened_images_path = "flattened_images.txt"

    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)

    gt_clean = _clean_ground_truth(ground_truth)
    if limit_to_first_n is not None:
        gt_clean = gt_clean[:limit_to_first_n]

    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Could not read: {image_path}")

    plates = DetectPlates.detectPlatesInScene(img)

    if len(plates) == 0:
        raise RuntimeError(f"No plates detected in {image_path}")

    # Avoid DetectChars.detectCharsInPlates() to prevent KNN crash during export.
    # Instead, extract ROIs from each candidate plate and pick the one with most ROIs.
    best_plate = None
    best_rois = []

    for p in plates:
        rois_candidate = _extract_char_rois_from_detected_plate(p)
        if len(rois_candidate) > len(best_rois):
            best_rois = rois_candidate
            best_plate = p

    rois = best_rois
    if len(rois) == 0:
        raise RuntimeError(f"No char ROIs extracted in {image_path}")


    # Ensure kNN recognizes with float32
    # (OpenCV asserts on sample dtype)
    # Here roi extraction uses cv2.resize which may return uint8; convert in-place later.


    # Map ROI index -> label by position.
    n = min(len(rois), len(gt_clean))
    if n == 0:
        raise RuntimeError(f"Ground truth cleaned to empty or length mismatch. gt_clean={gt_clean!r}")

    # Append only pairs that exist.
    for i in range(n):
        label_char = gt_clean[i]
        roi = rois[i]
        if roi.dtype != np.uint8 and roi.dtype != np.float32 and roi.dtype != np.int32:
            roi = roi.astype(np.uint8)

        _append_sample(
            roi,
            label_char,
            classifications_path=classifications_path,
            flattened_images_path=flattened_images_path,
        )


    print(f"[OK] Added {n} samples from {image_path}. gt_clean={gt_clean}")


if __name__ == "__main__":
    # Usage example:
    #   python add_samples_and_retrain.py
    # Will append samples for LicPlateImages/18.png and 21.png

    repo_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_root)

    pairs = [
        ("LicPlateImages/29.png", "A153TD")
    ]

    for img_path, gt in pairs:
        run(img_path, gt)


    # Retrain (side effect): reload+train from txt
    ok = DetectChars.loadKNNDataAndTrainKNN()
    if not ok:
        raise RuntimeError("KNN retraining failed")
    print("[OK] Retrained KNN with updated txt files.")

