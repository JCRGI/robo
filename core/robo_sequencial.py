
import os
import time
import threading
from typing import Optional, Tuple

from core.adb_manager import AdbManager
from core.detector_template import encontrar_botao_por_template

# Controle por porta (emulator-PORTA)
_running_single = {}
_threads_single = {}

def _log(msg: str):
    print(f"[ROBO_SINGLE] {msg}", flush=True)

def _connect_by_port(porta: int) -> Optional[AdbManager]:
    serial = f"emulator-{porta}"
    adb = AdbManager()
    adb.connect_device()
    # Seleciona explicitamente o device pela porta
    adb.device = next(d for d in adb.client.devices() if d.serial == serial)
    return adb

def _tap(adb: AdbManager, x: float, y: float):
    adb.device.shell(f"input tap {int(x)} {int(y)}")

def start_single_click_once(
    porta: int,
    template_path: str,
    conf: float = 0.82,
    timeout: float = 30.0,
    interval: float = 2.0,
    post_tap_delay: float = 1.0,
    tap_offset: Tuple[int, int] = (0, 0),
    debug_save: bool = False,
) -> None:
    """
    Inicia uma rotina em background que:
      - tira screenshots periódicas
      - procura o template alvo
      - ao encontrar, faz 1 clique e ENCERRA automaticamente

    Args:
        porta: porta do AVD (ex.: 5560)
        template_path: caminho absoluto do template do botão
        conf: limiar de confiança do template matching
        timeout: tempo máximo procurando (segundos)
        interval: intervalo entre screenshots (segundos)
        post_tap_delay: espera após o clique (segundos)
        tap_offset: (dx, dy) adicional no ponto de clique a partir do centro detectado
        debug_save: salva imagem debug com bounding box quando encontrar
    """
    if _running_single.get(porta, False):
        _log(f"Rotina já ativa na porta {porta}, ignorando novo start.")
        return

    _running_single[porta] = True

    def _runner():
        started_at = time.time()
        last_err = None
        try:
            adb = _connect_by_port(porta)
            _log(f"Monitorando template na porta {porta} (timeout={timeout}s).")

            while time.time() - started_at < timeout and _running_single.get(porta, False):
                screenshot = f"screenshot_auto_{porta}.png"
                try:
                    adb.capture_screen(screenshot)
                except Exception as e:
                    last_err = e
                    time.sleep(1.0)
                    continue

                match = None
                try:
                    match = encontrar_botao_por_template(
                        path_screenshot=screenshot,
                        path_template=template_path,
                        conf=conf,
                    )
                except Exception as e:
                    last_err = e

                if match:
                    cx = match["cx"] + tap_offset[0]
                    cy = match["cy"] + tap_offset[1]

                    _tap(adb, cx, cy)
                    _log(f"Clique em ({int(cx)}, {int(cy)}) score={match['score']:.2f} — encerrando rotina.")

                    if debug_save:
                        try:
                            import cv2
                            img = cv2.imread(screenshot)
                            x1, y1, x2, y2 = int(match["x1"]), int(match["y1"]), int(match["x2"]), int(match["y2"])
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            dbg = f"debug_box_{porta}.png"
                            cv2.imwrite(dbg, img)
                            _log(f"Debug salvo em {dbg}")
                        except Exception as _:
                            pass

                    time.sleep(post_tap_delay)
                    break  # encerra após o 1º clique
                time.sleep(interval)
        except StopIteration:
            _log(f"Device emulator-{porta} não encontrado via ADB.")
        except Exception as e:
            last_err = e
            _log(f"Erro na rotina: {e}")
        finally:
            _running_single[porta] = False
            if last_err:
                _log(f"Finalizado com erro: {last_err}")
            else:
                _log("Finalizado (sucesso/timeout).")

    th = threading.Thread(target=_runner, daemon=True)
    _threads_single[porta] = th
    th.start()

def is_running(porta: int) -> bool:
    return _running_single.get(porta, False)
