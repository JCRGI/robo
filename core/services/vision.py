from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List

import cv2
import numpy as np
import pytesseract
from flask import current_app


@dataclass
class DominantColor:
    hex: str
    percent: float

class VisionService:
    def __init__(self) -> None:
        # Respeita config do Flask se existir
        try:
            if current_app and current_app.config.get("TESSERACT_CMD"):
                pytesseract.pytesseract.tesseract_cmd = current_app.config["TESSERACT_CMD"]
        except RuntimeError:
            # fora do app context: ok
            pass

    def interpret(self, image_path: str, k_colors: int = 3) -> Dict[str, Any]:
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Não foi possível ler a imagem: {image_path}")
        h, w = img.shape[:2]

        ocr_items = self._ocr_with_boxes(img)
        boxes = self._find_boxes(img)
        colors = self._dominant_colors(img, k=k_colors)

        return {
            "width": w,
            "height": h,
            "dominant_colors": [c.__dict__ for c in colors],
            "ocr": ocr_items,
            "boxes": boxes,
        }

    def annotate(self, image_path: str, results: Dict[str, Any], out_path: str) -> str:
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Não foi possível ler a imagem: {image_path}")

        # caixas detectadas
        for b in results.get("boxes", []):
            x, y, w, h = int(b["x"]), int(b["y"]), int(b["w"]), int(b["h"])
            cv2.rectangle(img, (x, y), (x + w, y + h), (180, 180, 0), 2)

        # OCR boxes
        for o in results.get("ocr", []):
            x, y, w, h = int(o["x"]), int(o["y"]), int(o["w"]), int(o["h"])
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 160, 0), 2)
            txt = o["text"][:20]
            cv2.putText(img, txt, (x, max(12, y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 130, 0), 1, cv2.LINE_AA)

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        cv2.imwrite(out_path, img)
        return out_path

    def _ocr_with_boxes(self, img: np.ndarray) -> List[Dict[str, Any]]:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 7, 75, 75)
        thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 7)

        data = pytesseract.image_to_data(thr, lang="eng", output_type=pytesseract.Output.DICT)
        items: List[Dict[str, Any]] = []
        n = len(data.get("text", []))
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            conf = float(data.get("conf", ["-1"])[i])
            if not txt or conf < 60:
                continue
            x, y, w, h = int(data["left"][i]), int(data["top"][i]), int(data["width"][i]), int(data["height"][i])
            items.append({"text": txt, "conf": conf, "x": x, "y": y, "w": w, "h": h})
        return items

    def _find_boxes(self, img: np.ndarray) -> List[Dict[str, int]]:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 160)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = gray.shape[:2]
        area_img = w * h

        out: List[Dict[str, int]] = []
        for c in cnts:
            x, y, cw, ch = cv2.boundingRect(c)
            area = cw * ch
            if area < 0.002 * area_img or area > 0.9 * area_img:
                continue
            out.append({"x": int(x), "y": int(y), "w": int(cw), "h": int(ch)})
        return out

    def _dominant_colors(self, img: np.ndarray, k: int = 3) -> List[DominantColor]:
        # BGR -> RGB
        data = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS) # type: ignore
        counts = np.bincount(labels.flatten(), minlength=k).astype(float)
        perc = (counts / counts.sum()) * 100.0
        colors: List[DominantColor] = []
        for i, c in enumerate(centers.astype(int)):
            r, g, b = int(c[0]), int(c[1]), int(c[2])
            colors.append(DominantColor(hex=f"#{r:02x}{g:02x}{b:02x}", percent=round(float(perc[i]), 2)))
        colors.sort(key=lambda c: c.percent, reverse=True)
        return colors
