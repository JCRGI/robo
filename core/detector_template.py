
import cv2
import numpy as np
from typing import Optional, Dict

def encontrar_botao_por_template(
    path_screenshot: str,
    path_template: str,
    conf: float = 0.82,
    multi_escala=(0.75, 1.25, 11),
) -> Optional[Dict[str, float]]:
    """
    Encontra um botão específico via template matching multi-escala.
    Retorna bounding box e centro se achar com confiança >= conf.

    Args:
        path_screenshot: caminho da imagem de tela (PNG/JPG)
        path_template: caminho do recorte do botão
        conf: limiar de confiança (0..1)
        multi_escala: tupla (inicio, fim, passos) dos fatores de escala

    Returns:
        dict | None -> {"x1","y1","x2","y2","cx","cy","score"}
    """
    img = cv2.imread(path_screenshot, cv2.IMREAD_COLOR)
    tpl = cv2.imread(path_template,  cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Screenshot não encontrada: {path_screenshot}")
    if tpl is None:
        raise FileNotFoundError(f"Template não encontrado: {path_template}")

    h, w = tpl.shape[:2]
    best = None

    # Pré-processamento leve: conversão para escala de cinza melhora robustez
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tpl_gray = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)

    # Normaliza iluminação (opcional)
    img_gray = cv2.equalizeHist(img_gray)

    start, end, steps = multi_escala
    for scale in np.linspace(start, end, int(steps)):
        tw, th = int(w * scale), int(h * scale)
        if tw < 5 or th < 5:
            continue

        tpl_rs = cv2.resize(tpl_gray, (tw, th), interpolation=cv2.INTER_AREA)
        # pula se template maior que a imagem
        if th >= img_gray.shape[0] or tw >= img_gray.shape[1]:
            continue

        res = cv2.matchTemplate(img_gray, tpl_rs, cv2.TM_CCOEFF_NORMED)
        minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(res)

        if best is None or maxVal > best[0]:
            best = (maxVal, maxLoc, tw, th)

    if best and best[0] >= conf:
        score, (x, y), tw, th = best
        cx, cy = x + tw / 2.0, y + th / 2.0
        return {
            "x1": float(x),
            "y1": float(y),
            "x2": float(x + tw),
            "y2": float(y + th),
            "cx": float(cx),
            "cy": float(cy),
            "score": float(score),
        }
    return None
