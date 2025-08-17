from __future__ import annotations

from core.services.avd_clone import AvdCloneService
from core.services.emulators import EmulatorsService
from core.services.ocr import OcrService
from core.services.vision import VisionService


class CoreFacade:
    def __init__(self) -> None:
        self.emulators = EmulatorsService()
        self.ocr = OcrService()
        self.clone = AvdCloneService()
        self.vision = VisionService()


core = CoreFacade()
