from __future__ import annotations

from typing import List, Set

from core.errors import EmulatorError
from core.gateways import avd_manager as avd
from core.gateways import emulator_ctl as ctl
from core.locks import try_acquire_avd_start
from core.types import EmulatorDevice
from core.utils import normalizar_porta_console, portas_em_uso, proxima_porta_livre


class EmulatorsService:
    def list_avds(self) -> List[str]:
        return avd.listar_avds()

    def running_serials(self) -> Set[str]:
        return set(ctl.listar_emuladores_ativos())

    def start(
        self, avd_name: str, port: int | None = None, pacote: str | None = None, janela: bool = True, wait: bool = True
    ) -> int:
        """
        Inicia um AVD em porta par e livre. Retorna a porta usada.
        """
        try:
            # escolha determinística e válida
            if port is None:
                chosen_port: int = proxima_porta_livre()
            else:
                p = normalizar_porta_console(port)
                if p in portas_em_uso():
                    p = proxima_porta_livre(p + 2)
                chosen_port = p

            lock = try_acquire_avd_start(wait=True if wait else False, timeout=300.0)
            if lock is None:
                raise EmulatorError("Outro AVD está iniciando. Tente novamente em alguns instantes.")

            try:
                ctl.start_emulator(avd_name, chosen_port, modo_janela=janela)
                serial = f"emulator-{chosen_port}"
                if not ctl.wait_for_online(serial, timeout=90):
                    raise EmulatorError(f"Timeout esperando {serial} ficar online.")
                if not ctl.wait_for_boot_completed(serial, timeout=240):
                    raise EmulatorError(f"Timeout esperando boot do {serial}.")
                if pacote:
                    ctl.launch_app(serial, pacote)
            finally:
                try:
                    lock.release()
                except Exception:
                    pass

            return chosen_port

        except EmulatorError:
            raise
        except Exception as e:
            raise EmulatorError(f"Falha ao iniciar AVD '{avd_name}': {e}") from e

    def stop(self, serial: str) -> None:
        try:
            ctl.stop_emulator(serial)
        except Exception as e:
            raise EmulatorError(f"Falha ao parar emulador {serial}: {e}") from e

    def delete(self, avd_name: str) -> None:
        try:
            avd.deletar_avd(avd_name)
        except Exception as e:
            raise EmulatorError(f"Falha ao deletar AVD '{avd_name}': {e}") from e

    def snapshot(self) -> List[EmulatorDevice]:
        # nomes ordenados para mapeamento estável
        avds = sorted(self.list_avds())
        running = self.running_serials()
        base = normalizar_porta_console(5560)  # base sugerida (par)
        data: List[EmulatorDevice] = []
        for i, name in enumerate(avds):
            port = base + (2 * i)  # sempre PAR
            serial = f"emulator-{port}"
            status = "Rodando" if serial in running else "Desligado"
            data.append(EmulatorDevice(serial=serial, port=port, avd=name, status=status))
        return data
