from flask import Blueprint, request, jsonify
import os
import time
from datetime import datetime

from core.image_processor import (
    encontrar_horarios_menores,
    encontrar_horario_mais_proximo,
    selecionar_horario_disponivel,
    visualizar_horarios_detectados
)
from core.gateways import emulator_ctl
from core.multi_device_ocr import (
    ocr_manager,
    iniciar_busca_multi,
    parar_todas_buscas,
    obter_status_geral
)

# Criar Blueprint com prefixo '/ocr'
bp = Blueprint('ocr', __name__, url_prefix='/ocr')


# ========================================
# ROTAS SIMPLES (Single Device)
# ========================================

@bp.route('/detectar-horarios', methods=['POST'])
def detectar_horarios():
    """Detecta horários em uma imagem do emulador"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'erro': 'Body JSON não fornecido'}), 400
        
        serial = data.get('serial')
        horario_limite = data.get('horario_limite', '10:30 AM')
        
        if not serial or not serial.startswith('emulator-'):
            return jsonify({'erro': 'Serial inválido'}), 400
        
        # Verificar se emulador está ativo
        ativos = emulator_ctl.listar_emuladores_ativos()
        if serial not in ativos:
            return jsonify({
                'erro': f'Emulador {serial} não está ativo',
                'emuladores_ativos': ativos
            }), 404
        
        # Capturar e processar
        screenshot_path = f"temp/ocr_{serial.replace('emulator-', '')}.png"
        
        if not emulator_ctl.capture_screen(serial, screenshot_path):
            return jsonify({'erro': 'Falha ao capturar screenshot'}), 500
        
        if not os.path.exists(screenshot_path):
            return jsonify({'erro': 'Screenshot não foi criado'}), 500
        
        # Detectar horários
        horarios = encontrar_horarios_menores(screenshot_path, horario_limite)
        
        # Formatar resposta
        resultado = []
        for h in horarios:
            resultado.append({
                'horario': h['horario'],
                'hora_parseada': h['horario_parsed'].strftime('%H:%M'),
                'x': h['x'],
                'y': h['y'],
                'confianca': h['confianca'],
                'diferenca_minutos': h['diferenca_minutos']
            })
        
        # Limpar arquivo temporário
        try:
            os.remove(screenshot_path)
        except:
            pass
        
        return jsonify({
            'serial': serial,
            'horario_limite': horario_limite,
            'total_encontrados': len(resultado),
            'horarios': resultado
        })
        
    except Exception as e:
        import traceback
        print(f"\n[ERRO] detectar_horarios:")
        print(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


@bp.route('/selecionar-horario', methods=['POST'])
def selecionar_horario():
    """Seleciona automaticamente o horário mais próximo"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Body JSON não fornecido'}), 400
        
        serial = data.get('serial')
        horario_limite = data.get('horario_limite', '10:30 AM')
        
        if not serial or not serial.startswith('emulator-'):
            return jsonify({'erro': 'Serial inválido'}), 400
        
        ativos = emulator_ctl.listar_emuladores_ativos()
        if serial not in ativos:
            return jsonify({'erro': f'Emulador {serial} não está ativo'}), 404
        
        sucesso = selecionar_horario_disponivel(serial, horario_limite)
        
        if sucesso:
            return jsonify({
                'sucesso': True,
                'mensagem': f'Horário selecionado com sucesso',
                'serial': serial
            })
        else:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum horário disponível'
            }), 404
        
    except Exception as e:
        import traceback
        print(f"\n[ERRO] selecionar_horario:")
        print(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


@bp.route('/visualizar-horarios', methods=['POST'])
def visualizar_horarios():
    """Gera imagem com horários marcados"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Body JSON não fornecido'}), 400
        
        serial = data.get('serial')
        horario_limite = data.get('horario_limite', '10:30 AM')
        
        if not serial or not serial.startswith('emulator-'):
            return jsonify({'erro': 'Serial inválido'}), 400
        
        ativos = emulator_ctl.listar_emuladores_ativos()
        if serial not in ativos:
            return jsonify({'erro': f'Emulador {serial} não está ativo'}), 404
        
        screenshot_path = f"temp/ocr_{serial.replace('emulator-', '')}.png"
        
        if not emulator_ctl.capture_screen(serial, screenshot_path):
            return jsonify({'erro': 'Falha ao capturar screenshot'}), 500
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"static/ocr/horarios_{serial.replace('emulator-', '')}_{timestamp}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        visualizar_horarios_detectados(screenshot_path, horario_limite, output_path)
        
        try:
            os.remove(screenshot_path)
        except:
            pass
        
        return jsonify({
            'sucesso': True,
            'imagem': f"/{output_path}",
            'serial': serial
        })
        
    except Exception as e:
        import traceback
        print(f"\n[ERRO] visualizar_horarios:")
        print(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


@bp.route('/capturar-tela', methods=['POST'])
def capturar_tela():
    """Captura screenshot simples"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'erro': 'Body JSON não fornecido'}), 400
        
        serial = data.get('serial')
        
        if not serial or not serial.startswith('emulator-'):
            return jsonify({'erro': 'Serial inválido'}), 400
        
        ativos = emulator_ctl.listar_emuladores_ativos()
        if serial not in ativos:
            return jsonify({'erro': f'Emulador {serial} não está ativo'}), 404
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_path = f"static/screenshots/screenshot_{serial.replace('emulator-', '')}_{timestamp}.png"
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
        
        if emulator_ctl.capture_screen(serial, screenshot_path):
            return jsonify({
                'sucesso': True,
                'imagem': f"/{screenshot_path}",
                'serial': serial
            })
        else:
            return jsonify({'erro': 'Falha ao capturar screenshot'}), 500
        
    except Exception as e:
        import traceback
        print(f"\n[ERRO] capturar_tela:")
        print(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


# ========================================
# ROTAS MULTI-DISPOSITIVO
# ========================================

@bp.route('/busca-multi/iniciar', methods=['POST'])
def iniciar_busca_multi_route():
    """
    Inicia busca INFINITA em múltiplos dispositivos
    Sempre usa SWIPE para atualizar
    
    POST /ocr/busca-multi/iniciar
    Body: {
        "serials": ["emulator-5560"],
        "horario_limite": "10:30 AM",
        "intervalo": 3.0
    }
    """
    try:
        print("\n[DEBUG] Rota: /ocr/busca-multi/iniciar")
        
        data = request.get_json()
        print(f"[DEBUG] Body recebido: {data}")
        
        if not data:
            return jsonify({'erro': 'Body JSON não fornecido'}), 400
        
        serials = data.get('serials', [])
        horario_limite = data.get('horario_limite', '10:30 AM')
        intervalo = float(data.get('intervalo', 3.0))
        
        print(f"[DEBUG] Parâmetros:")
        print(f"  Serials: {serials}")
        print(f"  Horário limite: {horario_limite}")
        print(f"  Intervalo: {intervalo}")
        print(f"  Método: SWIPE (fixo)")
        print(f"  ⚠️ BUSCA INFINITA - Sem limite de tentativas!")
        
        if not serials:
            return jsonify({'erro': 'Lista de serials vazia'}), 400
        
        serials_invalidos = [s for s in serials if not s.startswith('emulator-')]
        if serials_invalidos:
            return jsonify({
                'erro': 'Serials com formato inválido',
                'serials_invalidos': serials_invalidos
            }), 400
        
        print(f"[DEBUG] Verificando emuladores ativos...")
        ativos = emulator_ctl.listar_emuladores_ativos()
        print(f"[DEBUG] Emuladores ativos: {ativos}")
        
        serials_inativos = [s for s in serials if s not in ativos]
        
        if serials_inativos:
            return jsonify({
                'erro': 'Emuladores não ativos',
                'serials_inativos': serials_inativos,
                'emuladores_ativos': ativos
            }), 404
        
        print(f"[DEBUG] Iniciando buscas INFINITAS com SWIPE...")
        resultados = iniciar_busca_multi(
            serials,
            horario_limite,
            intervalo
        )
        
        print(f"[DEBUG] Resultados: {resultados}")
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Busca INFINITA iniciada em {len(serials)} dispositivo(s)',
            'aviso': 'Busca continuará até encontrar horário ou ser parada manualmente',
            'resultados': resultados,
            'configuracao': {
                'horario_limite': horario_limite,
                'intervalo': intervalo,
                'metodo_atualizacao': 'SWIPE (fixo)',
                'modo': 'INFINITO'
            }
        })
        
    except Exception as e:
        import traceback
        print(f"\n[ERRO] iniciar_busca_multi_route:")
        print(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


@bp.route('/busca-multi/parar', methods=['POST'])
def parar_busca_multi_route():
    """Para todas as buscas"""
    try:
        data = request.get_json() or {}
        serial = data.get('serial')
        
        if serial:
            success = ocr_manager.parar_busca(serial)
            if success:
                return jsonify({'sucesso': True, 'mensagem': f'Busca parada: {serial}'})
            else:
                return jsonify({'erro': f'Dispositivo {serial} não está em busca'}), 404
        else:
            parar_todas_buscas()
            return jsonify({'sucesso': True, 'mensagem': 'Todas as buscas foram paradas'})
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/busca-multi/status', methods=['GET'])
def status_busca_multi():
    """Status geral"""
    try:
        status = obter_status_geral()
        return jsonify(status)
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/busca-multi/status/<serial>', methods=['GET'])
def status_dispositivo_multi(serial):
    """Status de um dispositivo"""
    try:
        estado = ocr_manager.obter_estado(serial)
        if estado:
            return jsonify(estado)
        else:
            return jsonify({'erro': f'Dispositivo {serial} não está em busca'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# ========================================
# ROTAS DE CONTROLE INDIVIDUAL
# ========================================

@bp.route('/dispositivo/<serial>/pausar', methods=['POST'])
def pausar_dispositivo(serial):
    """Pausa um dispositivo"""
    try:
        success = ocr_manager.pausar_busca(serial)
        if success:
            return jsonify({
                'sucesso': True,
                'mensagem': f'Busca pausada: {serial}',
                'serial': serial,
                'status': 'paused'
            })
        else:
            return jsonify({'erro': 'Não foi possível pausar'}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/dispositivo/<serial>/retomar', methods=['POST'])
def retomar_dispositivo(serial):
    """Retoma um dispositivo pausado"""
    try:
        success = ocr_manager.retomar_busca(serial)
        if success:
            return jsonify({
                'sucesso': True,
                'mensagem': f'Busca retomada: {serial}',
                'serial': serial,
                'status': 'searching'
            })
        else:
            return jsonify({'erro': 'Não foi possível retomar'}), 400
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/dispositivo/<serial>/parar', methods=['POST'])
def parar_dispositivo(serial):
    """Para um dispositivo"""
    try:
        success = ocr_manager.parar_busca(serial)
        if success:
            return jsonify({
                'sucesso': True,
                'mensagem': f'Busca parada: {serial}',
                'serial': serial,
                'status': 'stopped'
            })
        else:
            return jsonify({'erro': f'Dispositivo {serial} não está em busca'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/dispositivo/<serial>/reiniciar', methods=['POST'])
def reiniciar_dispositivo(serial):
    """Reinicia busca em um dispositivo"""
    try:
        ocr_manager.parar_busca(serial)
        time.sleep(0.5)
        
        estado = ocr_manager.obter_estado(serial)
        
        if estado:
            # Apenas 3 argumentos agora
            success = ocr_manager.iniciar_busca(
                serial,
                estado['horario_limite'],
                estado['intervalo']
            )
            
            if success:
                return jsonify({
                    'sucesso': True,
                    'mensagem': f'Busca INFINITA reiniciada: {serial}',
                    'serial': serial,
                    'configuracao': {
                        'horario_limite': estado['horario_limite'],
                        'intervalo': estado['intervalo'],
                        'metodo_atualizacao': 'SWIPE (fixo)',
                        'modo': 'INFINITO'
                    }
                })
        
        return jsonify({
            'erro': f'Não foi possível reiniciar {serial}'
        }), 400
        
    except Exception as e:
        import traceback
        print(f"\n[ERRO] reiniciar_dispositivo:")
        print(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500