import pytesseract
import cv2
import os

# Caminho do Tesseract no Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def process_image(path):
    print(f"Processando OCR da imagem: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Imagem não encontrada: {path}")

    imagem = cv2.imread(path)
    texto = pytesseract.image_to_string(imagem, lang='por')
    print("Texto reconhecido:")
    print(texto)
    return texto


def encontrar_texto_com_posicao(path, termos_procurados):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Imagem não encontrada: {path}")

    if isinstance(termos_procurados, str):
        termos_procurados = [termos_procurados]

    termos_procurados = [t.strip().lower() for t in termos_procurados]

    imagem = cv2.imread(path)

    resultados = pytesseract.image_to_data(
        imagem, lang='por', output_type=pytesseract.Output.DICT
    )

    for i in range(len(resultados["text"])):
        palavra = resultados["text"][i].strip().lower()
        x = resultados["left"][i]
        y = resultados["top"][i]
        w = resultados["width"][i]
        h = resultados["height"][i]

        for termo in termos_procurados:
            if termo in palavra:
                centro_x = x + w // 2
                centro_y = y + h // 2
                print(f"[OCR] '{termo}' detectado na palavra '{palavra}' em ({centro_x}, {centro_y})")
                return {
                    "texto_encontrado": palavra,
                    "x": centro_x,
                    "y": centro_y
                }

    return None