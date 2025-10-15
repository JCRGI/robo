"""Sistema de detecção de horários para múltiplos dispositivos com busca infinita"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from core.gateways import emulator_ctl
from core.image_processor import encontrar_horario_mais_proximo


class DeviceStatus(str, Enum):
    """Status possíveis de um dispositivo"""
    IDLE = "idle"
    SEARCHING = "searching"
    PAUSED = "paused"
    FOUND = "found"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class DeviceState:
    """Estado de um dispositivo na busca"""
    serial: str
    status: DeviceStatus = DeviceStatus.IDLE
    tentativas: int = 0
    horario_encontrado: Optional[Dict[str, Any]] = None
    ultimo_erro: Optional[str] = None
    ultima_atualizacao: datetime = field(default_factory=datetime.now)
    thread: Optional[threading.Thread] = None
    parado: bool = False
    pausado: bool = False
    horario_limite: str = "10:30 AM"
    intervalo: float = 3.0
    # metodo_refresh removido - sempre será swipe


class MultiDeviceOCR:
    """Gerenciador de busca de horários em múltiplos dispositivos"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceState] = {}
        self.callbacks: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {
            'on_found': [],
            'on_refresh': [],
            'on_error': [],
            'on_complete': [],
            'on_pause': [],
            'on_resume': []
        }
        self._lock = threading.Lock()
    
    def adicionar_callback(self, evento: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Adiciona callback para eventos"""
        if evento in self.callbacks:
            self.callbacks[evento].append(callback)
    
    def _trigger_callbacks(self, evento: str, serial: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Dispara callbacks de um evento"""
        for callback in self.callbacks.get(evento, []):
            try:
                callback(serial, data or {})
            except Exception as e:
                print(f"[ERRO] Callback {evento} falhou: {e}")
    
    def iniciar_busca(
        self,
        serial: str,
        horario_limite: str,
        intervalo_refresh: float = 3.0
    ) -> bool:
        """
        Inicia busca INFINITA de horário em um dispositivo.
        Sempre usa SWIPE para atualizar a tela.
        
        Args:
            serial: Serial do emulador
            horario_limite: Horário limite para busca
            intervalo_refresh: Segundos entre tentativas
        
        Returns:
            True se iniciou com sucesso
        """
        with self._lock:
            if serial in self.devices and self.devices[serial].status == DeviceStatus.SEARCHING:
                print(f"[AVISO] {serial} já está em busca ativa")
                return False
            
            if serial in self.devices and self.devices[serial].status == DeviceStatus.PAUSED:
                return self.retomar_busca(serial)
            
            self.devices[serial] = DeviceState(
                serial=serial,
                horario_limite=horario_limite,
                intervalo=intervalo_refresh
            )
        
        thread = threading.Thread(
            target=self._buscar_loop,
            args=(serial,),
            daemon=True
        )
        
        self.devices[serial].thread = thread
        thread.start()
        
        return True
    
    def pausar_busca(self, serial: str) -> bool:
        """Pausa a busca em um dispositivo"""
        with self._lock:
            if serial in self.devices and self.devices[serial].status == DeviceStatus.SEARCHING:
                self.devices[serial].pausado = True
                self.devices[serial].status = DeviceStatus.PAUSED
                self._trigger_callbacks('on_pause', serial)
                print(f"[INFO] Busca pausada: {serial}")
                return True
        return False
    
    def retomar_busca(self, serial: str) -> bool:
        """Retoma uma busca pausada"""
        with self._lock:
            if serial in self.devices and self.devices[serial].status == DeviceStatus.PAUSED:
                self.devices[serial].pausado = False
                self.devices[serial].status = DeviceStatus.SEARCHING
                self._trigger_callbacks('on_resume', serial)
                print(f"[INFO] Busca retomada: {serial}")
                return True
        return False
    
    def parar_busca(self, serial: str) -> bool:
        """Para a busca em um dispositivo (definitivo)"""
        with self._lock:
            if serial in self.devices:
                self.devices[serial].parado = True
                self.devices[serial].pausado = False
                self.devices[serial].status = DeviceStatus.STOPPED
                print(f"[INFO] Busca parada: {serial}")
                return True
        return False
    
    def parar_todas(self) -> None:
        """Para todas as buscas ativas"""
        with self._lock:
            for serial in list(self.devices.keys()):
                if serial in self.devices:
                    self.devices[serial].parado = True
                    self.devices[serial].pausado = False
                    self.devices[serial].status = DeviceStatus.STOPPED
    
    def obter_estado(self, serial: str) -> Optional[Dict[str, Any]]:
        """Retorna estado atual de um dispositivo"""
        with self._lock:
            if serial in self.devices:
                state = self.devices[serial]
                return {
                    'serial': serial,
                    'status': state.status.value,
                    'tentativas': state.tentativas,
                    'horario_encontrado': state.horario_encontrado,
                    'ultimo_erro': state.ultimo_erro,
                    'ultima_atualizacao': state.ultima_atualizacao.isoformat(),
                    'pausado': state.pausado,
                    'horario_limite': state.horario_limite,
                    'intervalo': state.intervalo
                }
        return None
    
    def obter_todos_estados(self) -> List[Dict[str, Any]]:
        """Retorna estado de todos os dispositivos"""
        with self._lock:
            estados: List[Dict[str, Any]] = []
            for serial in self.devices.keys():
                estado = self.obter_estado(serial)
                if estado is not None:
                    estados.append(estado)
            return estados
    
    def _buscar_loop(self, serial: str) -> None:
        """
        Loop INFINITO de busca para um dispositivo.
        Sempre usa SWIPE para atualizar.
        """
        state = self.devices[serial]
        state.status = DeviceStatus.SEARCHING
        
        print(f"\n{'='*70}")
        print(f"🔍 INICIANDO BUSCA INFINITA: {serial}")
        print(f"   Horário limite: {state.horario_limite}")
        print(f"   Intervalo: {state.intervalo}s")
        print(f"   Método: SWIPE (fixo)")
        print(f"   ⚠️ SEM LIMITE DE TENTATIVAS - Busca até encontrar!")
        print(f"{'='*70}\n")
        
        screenshot_path = f"temp/ocr_{serial.replace('emulator-', '')}.png"
        
        # LOOP INFINITO
        while not state.parado:
            if state.pausado:
                print(f"[{serial}] ⏸️ Pausado (tentativa {state.tentativas})...")
                time.sleep(1)
                continue
            
            state.tentativas += 1
            state.ultima_atualizacao = datetime.now()
            
            print(f"\n[{serial}] 🔄 Tentativa #{state.tentativas}")
            print(f"[{serial}] ⏰ {datetime.now().strftime('%H:%M:%S')}")
            
            try:
                # 1. ATUALIZAR TELA COM SWIPE (exceto primeira tentativa)
                if state.tentativas > 1:
                    print(f"[{serial}] 🔄 Atualizando tela com SWIPE...")
                    self._atualizar_tela_swipe(serial)
                    
                    self._trigger_callbacks('on_refresh', serial, {
                        'tentativa': state.tentativas,
                        'metodo': 'swipe'
                    })
                    
                    print(f"[{serial}] ⏳ Aguardando atualização da tela...")
                    time.sleep(2)
                
                # 2. CAPTURAR SCREENSHOT
                print(f"[{serial}] 📸 Capturando screenshot...")
                success = emulator_ctl.capture_screen(serial, screenshot_path)
                
                if not success:
                    raise Exception("Falha ao capturar screenshot")
                
                # 3. BUSCAR HORÁRIO
                print(f"[{serial}] 🔍 Buscando horários < {state.horario_limite}...")
                horario = encontrar_horario_mais_proximo(screenshot_path, state.horario_limite)
                
                # 4. VERIFICAR RESULTADO
                if horario:
                    # ✅ ENCONTROU!
                    print(f"\n{'='*70}")
                    print(f"[{serial}] ✅ HORÁRIO ENCONTRADO: {horario['horario']}")
                    print(f"[{serial}] 📍 Posição: ({horario['x']}, {horario['y']})")
                    print(f"[{serial}] 🔢 Após {state.tentativas} tentativa(s)")
                    print(f"{'='*70}\n")
                    
                    state.horario_encontrado = horario
                    state.status = DeviceStatus.FOUND
                    
                    print(f"[{serial}] 🖱️ Clicando no horário...")
                    emulator_ctl.tap(serial, horario['x'], horario['y'])
                    
                    self._trigger_callbacks('on_found', serial, {
                        'horario': horario,
                        'tentativa': state.tentativas
                    })
                    
                    break
                
                else:
                    print(f"[{serial}] ⚠️ Nenhum horário disponível")
                    print(f"[{serial}] 🔄 Continuando busca em {state.intervalo}s...")
                    
                    if not state.parado and not state.pausado:
                        time.sleep(state.intervalo)
                
            except Exception as e:
                print(f"[{serial}] ❌ ERRO: {e}")
                state.ultimo_erro = str(e)
                
                self._trigger_callbacks('on_error', serial, {
                    'erro': str(e),
                    'tentativa': state.tentativas
                })
                
                print(f"[{serial}] ⏳ Aguardando {state.intervalo}s antes de nova tentativa...")
                if not state.parado and not state.pausado:
                    time.sleep(state.intervalo)
        
        # Finalizar
        if state.parado:
            print(f"\n[{serial}] ⏹️ Busca parada pelo usuário após {state.tentativas} tentativas")
            state.status = DeviceStatus.STOPPED
        elif state.pausado:
            print(f"\n[{serial}] ⏸️ Busca pausada após {state.tentativas} tentativas")
            state.status = DeviceStatus.PAUSED
        
        if not state.pausado:
            self._trigger_callbacks('on_complete', serial, {
                'status': state.status.value,
                'tentativas': state.tentativas,
                'horario_encontrado': state.horario_encontrado
            })
        
        print(f"\n{'='*70}")
        print(f"🏁 BUSCA FINALIZADA: {serial}")
        print(f"   Status: {state.status.value}")
        print(f"   Total de tentativas: {state.tentativas}")
        print(f"{'='*70}\n")
    
    def _atualizar_tela_swipe(self, serial: str) -> None:
        """
        Atualiza a tela do emulador usando SWIPE (único método).
        """
        try:
            print(f"[{serial}] 📱 Obtendo tamanho da tela...")
            size = emulator_ctl.get_screen_size(serial)
            
            if size:
                width, height = size
                x_center = width // 2
                y_top = height // 5  # 20% do topo
                y_bottom = height * 4 // 5  # 80% da altura
                
                print(f"[{serial}] 👇 Swipe DOWN: ({x_center},{y_top}) -> ({x_center},{y_bottom})")
                emulator_ctl.swipe(serial, x_center, y_top, x_center, y_bottom, duration=600)
                time.sleep(1.5)
                
                print(f"[{serial}] 👆 Swipe UP: ({x_center},{y_bottom}) -> ({x_center},{y_top})")
                emulator_ctl.swipe(serial, x_center, y_bottom, x_center, y_top, duration=600)
            else:
                # Fallback com coordenadas padrão (1080x1920)
                print(f"[{serial}] ⚠️ Usando coordenadas padrão (1080x1920)")
                emulator_ctl.swipe(serial, 540, 384, 540, 1536, duration=600)
                time.sleep(1.5)
                emulator_ctl.swipe(serial, 540, 1536, 540, 384, duration=600)
            
            time.sleep(1)
            print(f"[{serial}] ✅ Tela atualizada com SWIPE")
            
        except Exception as e:
            print(f"[{serial}] ❌ Falha ao atualizar tela: {e}")


# Instância global
ocr_manager = MultiDeviceOCR()


# Funções de conveniência
def iniciar_busca_multi(
    serials: List[str],
    horario_limite: str,
    intervalo: float = 3.0
) -> Dict[str, bool]:
    """
    Inicia busca INFINITA em múltiplos dispositivos.
    Sempre usa SWIPE para atualizar.
    """
    resultados: Dict[str, bool] = {}
    for serial in serials:
        success = ocr_manager.iniciar_busca(
            serial,
            horario_limite,
            intervalo
        )
        resultados[serial] = success
    return resultados


def parar_todas_buscas() -> None:
    """Para todas as buscas ativas"""
    ocr_manager.parar_todas()


def obter_status_geral() -> Dict[str, Any]:
    """Retorna status geral de todas as buscas"""
    estados = ocr_manager.obter_todos_estados()
    return {
        'total': len(estados),
        'searching': sum(1 for e in estados if e['status'] == 'searching'),
        'paused': sum(1 for e in estados if e['status'] == 'paused'),
        'found': sum(1 for e in estados if e['status'] == 'found'),
        'error': sum(1 for e in estados if e['status'] == 'error'),
        'stopped': sum(1 for e in estados if e['status'] == 'stopped'),
        'devices': estados
    }