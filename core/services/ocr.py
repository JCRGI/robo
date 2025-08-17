from __future__ import annotations
import time
import os
from typing import Dict, Optional
import xml.etree.ElementTree as ET

import pytesseract
from flask import current_app

from core.adapters.adb_adapter import AdbAdapter
from core.detector_template import encontrar_botao_por_template
from core.errors import ADBError, OCRError
from core.image_processor import process_image


class OcrService:
    def __init__(self, adb: AdbAdapter | None = None) -> None:
        # mantemos atributo para compatibilidade, mas criaremos instâncias locais
        self.adb = adb or AdbAdapter()

    def ocr_text_from_serial(self, serial: str) -> str:
        screenshot = None
        adapter = AdbAdapter()
        try:
            adapter.ensure_ready(serial)
            screenshot = f"screenshots/screenshot_{serial.replace(':', '_')}.png"
            adapter.capture_screen_for(serial, screenshot)
            return process_image(screenshot)
        except ADBError:
            raise
        except Exception as e:
            raise OCRError(f"Falha no OCR: {e}") from e
        finally:
            if screenshot:
                try:
                    os.remove(screenshot)
                except Exception:
                    pass

    def click_template(self, serial: str, template_relpath: str, conf: float = 0.82) -> bool:
        screenshot = None
        adapter = AdbAdapter()
        try:
            adapter.ensure_ready(serial)
            screenshot = f"screenshots/screenshot_{serial.replace(':', '_')}.png"
            adapter.capture_screen_for(serial, screenshot)

            base = current_app.root_path if current_app else os.getcwd()
            template = os.path.join(base, template_relpath)

            match = encontrar_botao_por_template(
                path_screenshot=screenshot,
                path_template=template,
                conf=conf,
            )
            if not match:
                return False
            adapter.tap_for(serial, int(match["cx"]), int(match["cy"]))
            return True
        except ADBError:
            raise
        except Exception as e:
            raise OCRError(f"Falha ao clicar por template: {e}") from e
        finally:
            if screenshot:
                try:
                    os.remove(screenshot)
                except Exception:
                    pass

    def _find_text_position(self, image_path: str, query: str) -> Optional[Dict[str, int]]:
        """
        Retorna o bbox do primeiro item de OCR que contém 'query' (case-insensitive).
        """
        data = pytesseract.image_to_data(image_path, lang="eng", output_type=pytesseract.Output.DICT)
        q = (query or "").strip().lower()
        n = len(data.get("text", []))
        for i in range(n):
            txt = (data["text"][i] or "").strip()
            if not txt:
                continue
            if q in txt.lower():
                x, y = int(data["left"][i]), int(data["top"][i])
                w, h = int(data["width"][i]), int(data["height"][i])
                # centro do bbox
                return {"x": x + w // 2, "y": y + h // 2, "w": w, "h": h}
        return None

    def click_text(self, serial: str, texto: str) -> bool:
        """
        Captura screenshot do 'serial', procura 'texto' e toca no centro do bbox.
        """
        screenshot = None
        adapter = AdbAdapter()
        try:
            adapter.ensure_ready(serial)
            screenshot = f"screenshot_{serial.replace(':', '_')}.png"
            adapter.capture_screen_for(serial, screenshot)
            pos = self._find_text_position(screenshot, texto)
            if not pos:
                return False
            adapter.tap_for(serial, int(pos["x"]), int(pos["y"]))
            return True
        except ADBError:
            raise
        except Exception as e:
            raise OCRError(f"Falha ao clicar no texto '{texto}': {e}") from e
        finally:
            if screenshot:
                try:
                    os.remove(screenshot)
                except Exception:
                    pass

    def click_text_with_scroll(self, serial: str, texto: str, tentativas: int = 10, delay: float = 1.5) -> bool:
        """
        Tenta encontrar e clicar no 'texto' fazendo scroll vertical entre tentativas.
        """
        adapter = AdbAdapter()
        try:
            adapter.ensure_ready(serial)
            for _ in range(max(1, int(tentativas))):
                screenshot = f"screenshot_{serial.replace(':', '_')}.png"
                try:
                    adapter.capture_screen_for(serial, screenshot)
                    pos = self._find_text_position(screenshot, texto)
                finally:
                    try:
                        os.remove(screenshot)
                    except Exception:
                        pass
                if pos:
                    adapter.tap_for(serial, int(pos["x"]), int(pos["y"]))
                    return True
                # swipe up
                adapter.shell_for(serial, "input swipe 300 1000 300 500")
                time.sleep(max(0.0, float(delay)))
            return False
        except ADBError:
            raise
        except Exception as e:
            raise OCRError(f"Falha ao buscar/clicar no texto '{texto}': {e}") from e

    def _parse_bounds(self, bounds: str) -> Optional[Dict[str, int]]:
        # bounds no formato: [x1,y1][x2,y2]
        try:
            parts = bounds.replace("[", " ").replace("]", " ").split()
            x1, y1 = (int(v) for v in parts[0].split(","))
            x2, y2 = (int(v) for v in parts[1].split(","))
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            return {"x": cx, "y": cy, "w": x2 - x1, "h": y2 - y1}
        except Exception:
            return None

    def click_text_uia(self, serial: str, texto: str, tentativas: int = 12, delay: float = 1.0) -> bool:
        """
        Procura nó com text ou content-desc contendo 'texto' e clica. Faz scroll até encontrar.
        """
        adapter = AdbAdapter()
        query = (texto or "").strip().lower()
        if not query:
            raise OCRError("Texto alvo vazio.")

        try:
            adapter.ensure_ready(serial)
            for _ in range(max(1, int(tentativas))):
                xml = adapter.dump_ui_xml(serial, compressed=True)
                # alguns devices escrevem o caminho no stdout; filtra linhas inválidas
                xml_str = "\n".join([ln for ln in xml.splitlines() if ln.strip().startswith("<")])
                try:
                    root = ET.fromstring(xml_str)
                except Exception:
                    # tenta novamente após pequeno delay
                    time.sleep(delay)
                    continue

                hit = None
                for node in root.iter():
                    txt = (node.attrib.get("text") or "").strip()
                    desc = (node.attrib.get("content-desc") or "").strip()
                    if (txt and query in txt.lower()) or (desc and query in desc.lower()):
                        hit = node
                        break

                if hit:
                    b = self._parse_bounds(hit.attrib.get("bounds", ""))
                    if b:
                        adapter.tap_for(serial, int(b["x"]), int(b["y"]))
                        return True

                # não achou, faz scroll
                adapter.shell_for(serial, "input swipe 300 1100 300 400")
                time.sleep(max(0.0, float(delay)))

            # fallback para OCR com scroll
            return self.click_text_with_scroll(serial, texto, tentativas=5, delay=1.2)

        except ADBError:
            raise
        except Exception as e:
            raise OCRError(f"Falha ao clicar via UIAutomator em '{texto}': {e}") from e

    def auto_click_purchase(self, serial: str, tentativas: int = 12, delay: float = 1.0) -> None:
        """
        Tenta encontrar e clicar no botão 'Purchase' automaticamente.
        Usa UIAutomator com scroll e, se falhar, faz fallback para OCR com scroll.
        Executa sem levantar exceções (log/print apenas).
        """
        try:
            # pequena espera para a tela estabilizar após abrir o app
            time.sleep(2.0)
            ok = self.click_text_uia(serial, "Purchase", tentativas=tentativas, delay=delay)
            if not ok:
                _ = self.click_text_with_scroll(serial, "Purchase", tentativas=5, delay=delay)
        except Exception as e:
            print(f"[auto_click_purchase] {serial}: {e}")
