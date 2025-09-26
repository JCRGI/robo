from __future__ import annotations

from core.services.avd_clone import AvdCloneService
from core.services.emulators import EmulatorsService
from core.services.notify import NotifyService
from core.services.runtime_bots import RuntimeBotsService
from core.services.ocr import OcrService
from core.adapters.adb_adapter import AdbAdapter
from core.services.vision import VisionService


class CoreFacade:
    def __init__(self) -> None:
        self.emulators = EmulatorsService()
        self.ocr = OcrService()
        self.adb = AdbAdapter()
        self.clone = AvdCloneService()
        self.vision = VisionService()
        self.notify = NotifyService()
        self.runtime_bots = RuntimeBotsService(self.ocr, self.adb, self.notify)


core = CoreFacade()
