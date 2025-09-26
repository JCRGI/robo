from __future__ import annotations
import threading, time
from dataclasses import dataclass
from typing import Optional, Dict, Callable

from core.services.ocr import OcrService  # já existe
from core.adapters.adb_adapter import AdbAdapter
from core.services.notify import NotifyService

@dataclass
class BotConfig:
    serial: str
    texto_alvo: str
    novo_texto: Optional[str] = None
    intervalo: float = 3.0
    max_ciclos: Optional[int] = None
    usar_swipe: bool = True
    espera_pos_swipe: float = 1.5
    notify_whatsapp: bool = False  # NOVO

@dataclass
class BotStatus:
    running: bool
    paused: bool
    cycles: int
    last_result: Optional[str]
    config: BotConfig

class SessionBot:
    def __init__(self, cfg: BotConfig, ocr: OcrService, adb: AdbAdapter, notifier: NotifyService | None):
        self.cfg = cfg
        self._ocr = ocr
        self._adb = adb
        self._notifier = notifier
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._lock = threading.Lock()
        self.cycles = 0
        self.last_result: Optional[str] = None
        self._sent_notification = False  # NOVO

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self, value: bool):
        if value:
            self._pause.set()
        else:
            self._pause.clear()

    def stop(self):
        self._stop.set()
        self._pause.clear()

    def status(self) -> BotStatus:
        return BotStatus(
            running=bool(self._thread and self._thread.is_alive() and not self._stop.is_set()),
            paused=self._pause.is_set(),
            cycles=self.cycles,
            last_result=self.last_result,
            config=self.cfg
        )

    # Core loop
    def _run(self):
        try:
            # detectar tamanho de tela (uma vez) para calcular swipe
            swipe_coords = None
            if self.cfg.usar_swipe:
                try:
                    out = self._adb.shell_for(self.cfg.serial, "wm size")  # ex: Physical size: 1080x1920
                    for part in out.split():
                        if "x" in part and part.replace("x", "").isdigit() is False:
                            # part tipo "1080x1920"
                            w_h = part.strip().split("x")
                            if len(w_h) == 2 and all(p.isdigit() for p in w_h):
                                w, h = map(int, w_h)
                                x = w // 2
                                y_start = int(h * 0.70)
                                y_end = int(h * 0.30)
                                swipe_coords = (x, y_start, x, y_end, 400)  # duração 400ms
                                break
                except Exception:
                    swipe_coords = None  # fallback: ignora swipe se falhar
            while not self._stop.is_set():
                if self._pause.is_set():
                    time.sleep(0.4)
                    continue

                self.cycles += 1
                ciclo = self.cycles
                try:
                    # 1. Swipe de refresh
                    if self.cfg.usar_swipe and swipe_coords:
                        x1, y1, x2, y2, dur = swipe_coords
                        self._adb.shell_for(
                            self.cfg.serial,
                            f"input swipe {x1} {y1} {x2} {y2} {dur}"
                        )
                        time.sleep(self.cfg.espera_pos_swipe)

                    # 2. Busca do texto (UIAutomator click)
                    achou = self._ocr.click_text_uia(
                        self.cfg.serial,
                        self.cfg.texto_alvo,
                        tentativas=1,
                        delay=0.3
                    )

                    if achou and not self._sent_notification and self.cfg.notify_whatsapp and self._notifier:
                        self._notifier.notify_found(self.cfg.serial, self.cfg.texto_alvo, ciclo)
                        self._sent_notification = True
                    if achou and self.cfg.novo_texto:
                        # foco dado pelo clique; limpar e digitar novo texto
                        self._adb.shell_for(self.cfg.serial, "input keyevent 123")  # END
                        for _ in range(40):
                            self._adb.shell_for(self.cfg.serial, "input keyevent 67")  # DEL
                        safe_txt = self.cfg.novo_texto.replace(" ", "%s")
                        self._adb.shell_for(self.cfg.serial, f"input text {safe_txt}")
                        self.last_result = f"ciclo {ciclo}: encontrado e atualizado"
                    elif achou:
                        self.last_result = f"ciclo {ciclo}: encontrado"
                    else:
                        self.last_result = f"ciclo {ciclo}: NÃO encontrado"
                except Exception as e:
                    self.last_result = f"ciclo {ciclo}: erro {e}"

                if self.cfg.max_ciclos and self.cycles >= self.cfg.max_ciclos:
                    break
                time.sleep(max(0.2, self.cfg.intervalo))
        finally:
            self._stop.set()

class RuntimeBotsService:
    def __init__(self, ocr: OcrService, adb: AdbAdapter, notifier: NotifyService | None):
        self._ocr = ocr
        self._adb = adb
        self._notifier = notifier
        self._bots: Dict[str, SessionBot] = {}
        self._lock = threading.Lock()

    def start_bot(self, serial: str, texto_alvo: str, novo_texto: Optional[str],
                  intervalo: float, notify_whatsapp: bool = False) -> BotStatus:
        cfg = BotConfig(serial=serial, texto_alvo=texto_alvo, novo_texto=novo_texto,
                        intervalo=intervalo, notify_whatsapp=notify_whatsapp)
        with self._lock:
            bot = self._bots.get(serial)
            if bot and bot.status().running:
                raise ValueError("Já existe um bot rodando neste emulador.")
            bot = SessionBot(cfg, self._ocr, self._adb, self._notifier)
            self._bots[serial] = bot
            bot.start()
            return bot.status()

    def pause_bot(self, serial: str, pause: bool) -> BotStatus:
        bot = self._bots.get(serial)
        if not bot:
            raise ValueError("Bot não encontrado.")
        bot.pause(pause)
        return bot.status()

    def stop_bot(self, serial: str) -> BotStatus:
        bot = self._bots.get(serial)
        if not bot:
            raise ValueError("Bot não encontrado.")
        bot.stop()
        return bot.status()

    def get_status(self, serial: str) -> BotStatus | None:
        bot = self._bots.get(serial)
        return bot.status() if bot else None

    def list_status(self) -> Dict[str, BotStatus]:
        return {k: b.status() for k, b in self._bots.items()}