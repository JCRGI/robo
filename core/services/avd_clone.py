from __future__ import annotations

from core.duplicador_avd import duplicar_avd_em_background, obter_status


class AvdCloneService:
    def start(self, base: str, novo: str) -> str:
        return duplicar_avd_em_background(base, novo)

    def status(self, task_id: str) -> dict:
        return obter_status(task_id)
