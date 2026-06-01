import os
import cv2
import numpy as np

import DetectPlates
import DetectChars
import Preprocess


def _extract_char_rois_from_plate_image(img_bgr: np.ndarray, plate) -> list[np.ndarray]:
    # Mirror logic in DetectChars pipeline: preprocess -> resize thresh -> OTSU
    # img_bgr is unused; plate.imgPlate already contains the cropped plate.
    plate.imgGrayscale, plate.imgThresh = Preprocess.preprocess(plate.imgPlate)


    plate.imgThresh = cv2.resize(plate.imgThresh, (0, 0), fx=1.6, fy=1.6)
    _, plate.imgThresh = cv2.threshold(
        plate.imgThresh, 0.0, 255.0, cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )

    listOfPossibleCharsInPlate = DetectChars.findPossibleCharsInPlate(
        plate.imgGrayscale, plate.imgThresh
    )
    listOfListsOfMatchingCharsInPlate = DetectChars.findListOfListsOfMatchingChars(
        listOfPossibleCharsInPlate
    )

    if len(listOfListsOfMatchingCharsInPlate) == 0:
        return []

    for i in range(0, len(listOfListsOfMatchingCharsInPlate)):
        listOfListsOfMatchingCharsInPlate[i].sort(key=lambda ch: ch.intCenterX)
        listOfListsOfMatchingCharsInPlate[i] = DetectChars.removeInnerOverlappingChars(
            listOfListsOfMatchingCharsInPlate[i]
        )

    longest = max(listOfListsOfMatchingCharsInPlate, key=lambda g: len(g))
    longest.sort(key=lambda ch: ch.intCenterX)

    rois = []
    for ch in longest:
        x, y, w, h = (
            ch.intBoundingRectX,
            ch.intBoundingRectY,
            ch.intBoundingRectWidth,
            ch.intBoundingRectHeight,
        )
        roi = plate.imgThresh[y : y + h, x : x + w]
        roi_resized = cv2.resize(roi, (20, 30), interpolation=cv2.INTER_NEAREST)
        rois.append(roi_resized)

    return rois


def _predict_from_roi_20x30(roi_20x30: np.ndarray) -> str:
    # Same as DetectChars.recognizeCharsInPlate
    # KNN is module-level inside DetectChars
    roi = roi_20x30
    if roi.dtype != np.uint8:
        roi = roi.astype(np.uint8)

    npaROIResized = roi.reshape((1, 20 * 30)).astype(np.float32)
    _, npaResults, _, _ = DetectChars.kNearest.findNearest(npaROIResized, k=1)
    code = int(npaResults[0][0])
    return chr(code)


def _clean_gt(s: str) -> str:
    s = s.upper()
    return "".join(ch for ch in s if ("0" <= ch <= "9") or ("A" <= ch <= "Z"))


def run_one(image_path: str, ground_truth: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Could not read: {image_path}")

    gt_clean = _clean_gt(ground_truth)

    plates = DetectPlates.detectPlatesInScene(img)
    if len(plates) == 0:
        raise RuntimeError(f"No plates detected in {image_path}")

    # pick plate with most extracted ROIs
    best_plate = None
    best_rois = []
    for p in plates:
        rois = _extract_char_rois_from_plate_image(img, p)
        if len(rois) > len(best_rois):
            best_rois = rois
            best_plate = p

    rois = best_rois

    pred_chars = []
    for i, roi in enumerate(rois):
        pred = _predict_from_roi_20x30(roi)
        pred_chars.append(pred)

        cv2.imwrite(os.path.join(out_dir, f"roi_{i:02d}_pred_{pred}.png"), roi)

    # save summary json-ish txt
    # map gt by index (left-to-right)
    n = min(len(rois), len(gt_clean))
    lines = []
    lines.append(f"image={image_path}")
    lines.append(f"gt_raw={ground_truth}")
    lines.append(f"gt_clean={gt_clean}")
    lines.append(f"num_rois={len(rois)}")
    lines.append(f"pred_str={''.join(pred_chars)}")

    for i in range(n):
        lines.append(f"idx={i} gt={gt_clean[i]} pred={pred_chars[i]} {'OK' if gt_clean[i]==pred_chars[i] else 'WRONG'}")

    with open(os.path.join(out_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("[OK]", "\n".join(lines[-5:]))


if __name__ == "__main__":
    # IMPORTANT: run after KNN trained
    ok = DetectChars.loadKNNDataAndTrainKNN()
    if not ok:
        raise RuntimeError("KNN training failed")

    repo_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_root)

    pairs = [
        ("LicPlateImages/32.png", "99H77060")
    ]

    for img_path, gt in pairs:
        out_dir = os.path.join("tmp_rois_debug", os.path.basename(img_path).replace(".png", ""))
        run_one(img_path, gt, out_dir)

