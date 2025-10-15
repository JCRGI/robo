from flask import Blueprint, request, jsonify, send_file
import subprocess
import threading
import time
from typing import List, Dict, Any, Optional
import os

ocr_bp = Blueprint('ocr', __name__, url_prefix='/ocr')

# Armazenar status das buscas ativas
buscas_ativas: Dict[str, Dict[str, Any]] = {}
lock = threading.Lock()

@ocr_bp.route('/emuladores/lista-ativos', methods=['GET'])
def listar_emuladores_ativos():
    """Lista todos os emuladores Android ativos"""
    try:
        result = subprocess.run(
            ['adb', 'devices'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        linhas = result.stdout.strip().split('\n')
        emuladores: List[Dict[str, str]] = []
        
        for linha in linhas[1:]:
            linha = linha.strip()
            if linha and '\t' in linha:
                partes = linha.split('\t')
                if len(partes) >= 2 and partes[1] == 'device':
                    serial = partes[0]
                    nome = serial
                    
                    if serial.startswith('emulator-'):
                        try:
                            nome_result = subprocess.run(
                                ['adb', '-s', serial, 'emu', 'avd', 'name'],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if nome_result.returncode == 0:
                                nome = nome_result.stdout.strip()
                        except:
                            pass
                    
                    emuladores.append({
                        'serial': serial,
                        'nome': nome
                    })
        
        return jsonify({
            'emuladores': emuladores,
            'total': len(emuladores)
        }), 200
    
    except Exception as e:
        return jsonify({
            'erro': str(e),
            'emuladores': []
        }), 500

@ocr_bp.route('/busca-area/iniciar', methods=['POST'])
def iniciar_busca_area():
    data = request.json
    if not data:
        return jsonify({'erro': 'Dados inválidos'}), 400
    
    serial = data.get('serial')
    horario_limite = data.get('horario_limite')
    area_busca = data.get('area_busca')
    
    if not serial or not horario_limite:
        return jsonify({'erro': 'Serial e horário limite são obrigatórios'}), 400
    
    # Iniciar thread de busca
    thread = threading.Thread(
        target=executar_busca_continua,
        args=(serial, horario_limite, area_busca)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'mensagem': 'Busca iniciada com sucesso'}), 200

@ocr_bp.route('/busca-area/status/<serial>', methods=['GET'])
def status_busca(serial: str):
    with lock:
        status = buscas_ativas.get(serial)
        if status is None:
            return jsonify({
                'status': 'not_found',
                'mensagem': 'Busca não encontrada'
            }), 404
        return jsonify(status), 200

@ocr_bp.route('/busca-area/parar', methods=['POST'])
def parar_busca():
    data = request.json
    if not data:
        return jsonify({'erro': 'Dados inválidos'}), 400
    
    serial = data.get('serial')
    if not serial:
        return jsonify({'erro': 'Serial é obrigatório'}), 400
    
    with lock:
        busca = buscas_ativas.get(serial)
        if busca is not None:
            busca['parar'] = True
            return jsonify({'mensagem': 'Comando de parada enviado'}), 200
        else:
            return jsonify({'erro': 'Busca não encontrada'}), 404

@ocr_bp.route('/busca-area/limpar-alerta', methods=['POST'])
def limpar_alerta():
    """Limpa flag de alerta após ser exibido"""
    data = request.json
    if not data:
        return jsonify({'erro': 'Dados inválidos'}), 400
    
    serial = data.get('serial')
    if not serial:
        return jsonify({'erro': 'Serial é obrigatório'}), 400
    
    with lock:
        busca = buscas_ativas.get(serial)
        if busca is not None:
            busca['alerta'] = False
            return jsonify({'mensagem': 'Alerta limpo'}), 200
        else:
            return jsonify({'erro': 'Busca não encontrada'}), 404

def executar_busca_continua(serial: str, horario_limite: str, area_busca: Dict[str, int]) -> None:
    """
    Executa busca contínua de horários em um emulador específico.
    Busca por até 5 segundos, depois atualiza a tela com swipe e repete.
    """
    # Inicializar status da busca
    with lock:
        buscas_ativas[serial] = {
            'status': 'searching',
            'tentativas': 0,
            'parar': False,
            'ultimo_swipe': None,
            'horario_encontrado': None
        }
    
    TIMEOUT_BUSCA = 5
    DELAY_APOS_SWIPE = 1.5
    
    try:
        print(f"\n[{serial}] ═══ INICIANDO PRIMEIRA ANÁLISE ═══")
        time.sleep(1)
        
        while True:
            # Verificar se deve parar
            with lock:
                busca = buscas_ativas.get(serial)
                if busca is None or busca.get('parar', False):
                    if busca is not None:
                        busca['status'] = 'stopped'
                    break
            
            tempo_inicio = time.time()
            horario_encontrado = None
            tentativas_ciclo = 0
            
            print(f"[{serial}] Iniciando ciclo de busca (até {TIMEOUT_BUSCA}s)...")
            
            while (time.time() - tempo_inicio) < TIMEOUT_BUSCA:
                with lock:
                    busca = buscas_ativas.get(serial)
                    if busca is None or busca.get('parar', False):
                        if busca is not None:
                            busca['status'] = 'stopped'
                        return
                
                tentativas_ciclo += 1
                
                with lock:
                    busca = buscas_ativas.get(serial)
                    if busca is not None:
                        busca['status'] = 'searching'
                        busca['tentativas'] = busca.get('tentativas', 0) + 1
                
                try:
                    print(f"[{serial}] Tentativa {tentativas_ciclo} - Capturando área...")
                    
                    screenshot = capturar_area(serial, area_busca)
                    
                    print(f"[{serial}] Screenshot capturado, processando OCR...")
                    
                    # Processar OCR e obter coordenadas
                    horarios = processar_ocr_area_com_coordenadas(screenshot, horario_limite, area_busca)
                    
                    if horarios:
                        print(f"[{serial}] ✅ HORÁRIO ENCONTRADO: {horarios[0]['horario']}")
                        horario_encontrado = horarios[0]
                        break
                    else:
                        print(f"[{serial}] Nenhum horário válido encontrado nesta tentativa")
                
                except Exception as e:
                    print(f"[{serial}] ⚠️ Erro na busca: {e}")
                    import traceback
                    traceback.print_exc()
                
                time.sleep(0.5)
            
            # Se encontrou, clicar e finalizar
            if horario_encontrado:
                with lock:
                    busca = buscas_ativas.get(serial)
                    if busca is not None:
                        busca['status'] = 'found'
                        busca['horario_encontrado'] = horario_encontrado
                
                # CLICAR NO HORÁRIO ENCONTRADO
                try:
                    print(f"\n[{serial}] 🎯 CLICANDO NO HORÁRIO: {horario_encontrado['horario']}")
                    clicar_coordenada(serial, horario_encontrado['x'], horario_encontrado['y'])
                    print(f"[{serial}] ✅ Clique executado com sucesso!")
                    
                    with lock:
                        busca = buscas_ativas.get(serial)
                        if busca is not None:
                            busca['clicado'] = True
                            busca['alerta'] = True  # Flag para disparar alerta no frontend
                    
                except Exception as e:
                    print(f"[{serial}] ❌ Erro ao clicar: {e}")
                    with lock:
                        busca = buscas_ativas.get(serial)
                        if busca is not None:
                            busca['erro_clique'] = str(e)
                
                print(f"[{serial}] ═══ BUSCA FINALIZADA COM SUCESSO ═══\n")
                break
            
            # Fazer swipe para atualizar
            print(f"[{serial}] Nenhum horário encontrado após {TIMEOUT_BUSCA}s, atualizando tela...")
            
            try:
                fazer_swipe(serial)
                
                with lock:
                    busca = buscas_ativas.get(serial)
                    if busca is not None:
                        busca['status'] = 'refreshing'
                        busca['ultimo_swipe'] = time.time()
                
                print(f"[{serial}] Swipe executado, aguardando {DELAY_APOS_SWIPE}s...")
                time.sleep(DELAY_APOS_SWIPE)
                
                print(f"[{serial}] Tela atualizada, reiniciando busca...\n")
                
            except Exception as e:
                print(f"[{serial}] ❌ Erro no swipe: {e}")
                with lock:
                    busca = buscas_ativas.get(serial)
                    if busca is not None:
                        busca['status'] = 'error'
                        busca['erro'] = f'Erro no swipe: {str(e)}'
                break
    
    except Exception as e:
        print(f"[{serial}] ❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        
        with lock:
            busca = buscas_ativas.get(serial)
            if busca is not None:
                busca['status'] = 'error'
                busca['erro'] = str(e)


def processar_ocr_area_com_coordenadas(screenshot: bytes, horario_limite: str, area_busca: Dict[str, int]) -> List[Dict[str, Any]]:
    """Processa OCR e retorna horários com coordenadas para clicar"""
    import io
    import re
    import os
    from PIL import Image, ImageEnhance
    
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except:
        print("[ERRO] Tesseract não disponível")
        return []
    
    debug_path = os.path.join(os.getcwd(), 'debug_ocr')
    os.makedirs(debug_path, exist_ok=True)
    
    image = Image.open(io.BytesIO(screenshot))
    timestamp = int(time.time() * 1000)
    
    # Melhorar imagem
    largura, altura = image.size
    image_resized = image.resize((largura * 3, altura * 3), Image.Resampling.LANCZOS)
    image_gray = image_resized.convert('L')
    image_enhanced = ImageEnhance.Contrast(image_gray).enhance(3.0)
    image_sharp = ImageEnhance.Sharpness(image_enhanced).enhance(2.0)
    threshold = 140
    image_bw = image_sharp.point(lambda p: 0 if p < threshold else 255, mode='1') # type: ignore
    
    # OCR com dados de posição
    data = pytesseract.image_to_data(image_bw, config='--psm 6 --oem 3', lang='eng', output_type=pytesseract.Output.DICT)
    
    print(f"[DEBUG] OCR detectou {len(data['text'])} elementos")
    
    # Procurar horários
    padroes = [
        r'(\d{1,2})\s*:\s*(\d{2})\s+(AM|PM)',
        r'(\d{1,2}):(\d{2})\s*(AM|PM)',
    ]
    
    horarios_com_coords = []
    
    for i, texto in enumerate(data['text']):
        if not texto.strip():
            continue
        
        # Verificar próximos elementos para formar horário completo
        texto_completo = texto
        for j in range(i+1, min(i+4, len(data['text']))):
            if data['text'][j].strip():
                texto_completo += ' ' + data['text'][j]
        
        for padrao in padroes:
            match = re.search(padrao, texto_completo, re.IGNORECASE)
            if match:
                hora_str = match.group(0).strip()
                
                # Calcular coordenada central do texto
                x = data['left'][i] // 3  # Dividir por 3 pois aumentamos 3x
                y = data['top'][i] // 3
                w = data['width'][i] // 3
                h = data['height'][i] // 3
                
                # Coordenada central na tela (somando offset da área)
                x_tela = area_busca['x1'] + x + (w // 2)
                y_tela = area_busca['y1'] + y + (h // 2)
                
                print(f"[DEBUG] Horário '{hora_str}' detectado em ({x_tela}, {y_tela})")
                
                try:
                    hora_minutos = converter_horario_para_minutos(hora_str)
                    horario_limite_obj = converter_horario_para_minutos(horario_limite)
                    diferenca = horario_limite_obj - hora_minutos
                    
                    if diferenca > 0:
                        horarios_com_coords.append({
                            'horario': hora_str,
                            'x': x_tela,
                            'y': y_tela,
                            'confianca': data['conf'][i],
                            'diferenca_minutos': diferenca,
                            'timestamp': timestamp
                        })
                        print(f"[DEBUG] ✅ Válido - {diferenca} min antes do limite")
                except Exception as e:
                    print(f"[DEBUG] Erro ao validar '{hora_str}': {e}")
    
    horarios_com_coords.sort(key=lambda x: x['diferenca_minutos'])
    return horarios_com_coords


def clicar_coordenada(serial: str, x: int, y: int) -> None:
    """Executa clique em coordenada específica no emulador"""
    import subprocess
    
    cmd = f'adb -s {serial} shell input tap {x} {y}'
    print(f"[DEBUG] Executando: {cmd}")
    
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=10)
    
    if result.returncode != 0:
        raise Exception(f"Erro ao clicar: {result.stderr.decode()}")
    
    print(f"[DEBUG] Clique executado em ({x}, {y})")

def fazer_swipe(serial: str) -> None:
    """Executa swipe de cima para baixo (pull to refresh) no emulador"""
    # Começar dentro da área da lista de experiências
    # Baseado na sua imagem: área começa em y=328
    cmd = f'adb -s {serial} shell input swipe 250 350 250 1500 350'
    subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=10)

def capturar_area(serial: str, area: Dict[str, int]) -> bytes:
    """Captura screenshot de uma área específica"""
    import io
    from PIL import Image
    
    # Capturar screenshot completo
    cmd = f'adb -s {serial} exec-out screencap -p'
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=10)
    
    if result.returncode != 0:
        raise Exception(f"Erro ao capturar screenshot")
    
    # Fazer crop da área especificada
    image = Image.open(io.BytesIO(result.stdout))
    cropped = image.crop((area['x1'], area['y1'], area['x2'], area['y2']))
    
    # Converter para bytes
    img_bytes = io.BytesIO()
    cropped.save(img_bytes, format='PNG')
    
    return img_bytes.getvalue()

def processar_ocr_area(screenshot: bytes, horario_limite: str) -> List[Dict[str, Any]]:
    """Processa OCR na área e retorna horários encontrados antes do limite"""
    import io
    import re
    import os
    from datetime import datetime, time as dt_time
    from PIL import Image, ImageEnhance, ImageFilter
    
    try:
        import pytesseract
        
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"[ERRO] Tesseract não encontrado: {e}")
            return []
    except ImportError:
        print("[ERRO] pytesseract não instalado")
        return []
    
    debug_path = os.path.join(os.getcwd(), 'debug_ocr')
    os.makedirs(debug_path, exist_ok=True)
    
    image = Image.open(io.BytesIO(screenshot))
    
    timestamp = int(time.time() * 1000)
    original_path = os.path.join(debug_path, f'{timestamp}_original.png')
    image.save(original_path)
    print(f"[DEBUG] Imagem original salva: {original_path}")
    
    largura, altura = image.size
    image = image.resize((largura * 3, altura * 3), Image.Resampling.LANCZOS)
    image_gray = image.convert('L')
    image_enhanced = ImageEnhance.Contrast(image_gray).enhance(3.0)
    image_sharp = ImageEnhance.Sharpness(image_enhanced).enhance(2.0)
    
    threshold = 140
    image_bw = image_sharp.point(lambda p: 0 if p < threshold else 255, mode='1') # type: ignore
    
    processed_path = os.path.join(debug_path, f'{timestamp}_processed.png')
    image_bw.save(processed_path)
    print(f"[DEBUG] Imagem processada salva: {processed_path}")
    
    configs = [
        '--psm 6 --oem 3',
        '--psm 11 --oem 3',
        '--psm 7 --oem 3',
    ]
    
    todos_textos = []
    
    for i, config in enumerate(configs):
        try:
            texto = pytesseract.image_to_string(image_bw, config=config, lang='eng')
            todos_textos.append(f"\n=== CONFIG {i+1}: {config} ===\n{texto}")
            print(f"[DEBUG OCR CONFIG {i+1}] Texto detectado:")
            print(texto)
        except Exception as e:
            print(f"[ERRO] Falha no OCR config {i+1}: {e}")
    
    texto_completo = '\n'.join(todos_textos)
    
    text_path = os.path.join(debug_path, f'{timestamp}_texto.txt')
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(f"Horário Limite: {horario_limite}\n")
        f.write("="*70 + "\n")
        f.write(texto_completo)
    
    # PADRÕES MAIS FLEXÍVEIS
    padroes = [
        r'(\d{1,2})\s*:\s*(\d{2})\s+(AM|PM)',  # 7:40 PM (com espaço)
        r'(\d{1,2}):(\d{2})\s*(AM|PM)',        # 7:40PM
        r'(\d{1,2}):(\d{2})\s*([AaPp][Mm])',  # 7:40pm
        r'(\d{1,2})\s*:\s*(\d{2})',            # 7:40 (24h)
    ]
    
    horarios_encontrados_raw = []
    
    print(f"\n[DEBUG] ═══ PROCURANDO HORÁRIOS NO TEXTO ═══")
    
    for padrao in padroes:
        matches = list(re.finditer(padrao, texto_completo, re.IGNORECASE))
        print(f"[DEBUG] Padrão '{padrao}' → {len(matches)} matches")
        
        for match in matches:
            hora_str = match.group(0).strip()
            print(f"[DEBUG]   → Match encontrado: '{hora_str}'")
            horarios_encontrados_raw.append(hora_str)
    
    # Remover duplicatas mantendo ordem
    horarios_unicos_str = []
    vistos = set()
    for h in horarios_encontrados_raw:
        h_upper = h.upper().replace(' ', '')
        if h_upper not in vistos:
            vistos.add(h_upper)
            horarios_unicos_str.append(h)
    
    print(f"\n[DEBUG] ═══════════════════════════════════════")
    print(f"[DEBUG] Horários únicos detectados: {horarios_unicos_str}")
    print(f"[DEBUG] Horário limite configurado: {horario_limite}")
    
    # CONVERTER E COMPARAR
    horarios_validos = []
    
    try:
        horario_limite_obj = converter_horario_para_minutos(horario_limite)
        print(f"[DEBUG] Horário limite = {horario_limite_obj} minutos ({horario_limite})")
        
        for hora_str in horarios_unicos_str:
            try:
                hora_minutos = converter_horario_para_minutos(hora_str)
                diferenca = horario_limite_obj - hora_minutos
                
                print(f"\n[DEBUG] Analisando: '{hora_str}'")
                print(f"[DEBUG]   → Convertido: {hora_minutos} minutos")
                print(f"[DEBUG]   → Diferença: {diferenca} minutos")
                
                # Aceitar apenas horários ANTES do limite
                if diferenca > 0:
                    horarios_validos.append({
                        'horario': hora_str,
                        'x': 0,
                        'y': 0,
                        'confianca': 85,
                        'diferenca_minutos': diferenca,
                        'timestamp': timestamp
                    })
                    print(f"[DEBUG]   ✅ VÁLIDO - está {diferenca} min ANTES do limite")
                else:
                    print(f"[DEBUG]   ❌ INVÁLIDO - está {abs(diferenca)} min DEPOIS do limite")
                    
            except Exception as e:
                print(f"[DEBUG]   ⚠️ ERRO ao processar: {e}")
                continue
    
    except Exception as e:
        print(f"[ERRO] Erro ao converter horário limite '{horario_limite}': {e}")
        return []
    
    horarios_validos.sort(key=lambda x: x['diferenca_minutos'])
    
    print(f"\n[DEBUG] ═══════════════════════════════════════")
    print(f"[DEBUG] RESULTADO FINAL:")
    print(f"[DEBUG]   Total detectados: {len(horarios_unicos_str)}")
    print(f"[DEBUG]   Válidos (antes do limite): {len(horarios_validos)}")
    if horarios_validos:
        print(f"[DEBUG]   Horários válidos:")
        for h in horarios_validos:
            print(f"[DEBUG]     - {h['horario']} (+{h['diferenca_minutos']} min)")
    print(f"[DEBUG] ═══════════════════════════════════════\n")
    
    with open(text_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*70 + "\n")
        f.write("ANÁLISE DE HORÁRIOS:\n")
        f.write(f"Horário limite: {horario_limite} ({horario_limite_obj} minutos)\n")
        f.write(f"Total detectados: {len(horarios_unicos_str)}\n")
        f.write(f"Válidos (antes do limite): {len(horarios_validos)}\n\n")
        
        f.write("Todos horários detectados:\n")
        for h in horarios_unicos_str:
            try:
                min_h = converter_horario_para_minutos(h)
                diff = horario_limite_obj - min_h
                status = "✅ VÁLIDO" if diff > 0 else "❌ INVÁLIDO"
                f.write(f"  - {h} = {min_h} min ({status}, diff: {diff} min)\n")
            except:
                f.write(f"  - {h} = ERRO AO CONVERTER\n")
        
        f.write("\nHorários válidos (antes do limite):\n")
        if horarios_validos:
            for h in horarios_validos:
                f.write(f"  - {h['horario']} (diferença: +{h['diferenca_minutos']} min)\n")
        else:
            f.write("  Nenhum horário válido encontrado.\n")
    
    return horarios_validos


def converter_horario_para_minutos(horario_str: str) -> int:
    """
    Converte string de horário para minutos desde meia-noite.
    Suporta formatos: "2:35 PM", "14:35", "2:35 pm", etc.
    """
    import re
    
    horario_str = horario_str.strip().upper()
    
    # Tentar formato 12 horas (com AM/PM)
    match_12h = re.match(r'(\d{1,2})[:\s]*(\d{2})\s*(AM|PM)', horario_str)
    if match_12h:
        hora = int(match_12h.group(1))
        minuto = int(match_12h.group(2))
        periodo = match_12h.group(3)
        
        # Validar
        if hora < 1 or hora > 12:
            raise ValueError(f"Hora inválida: {hora}")
        if minuto < 0 or minuto > 59:
            raise ValueError(f"Minuto inválido: {minuto}")
        
        # Converter para 24h
        if periodo == 'PM' and hora != 12:
            hora += 12
        elif periodo == 'AM' and hora == 12:
            hora = 0
        
        return hora * 60 + minuto
    
    # Tentar formato 24 horas
    match_24h = re.match(r'(\d{1,2})[:\s]*(\d{2})$', horario_str)
    if match_24h:
        hora = int(match_24h.group(1))
        minuto = int(match_24h.group(2))
        
        # Validar
        if hora < 0 or hora > 23:
            raise ValueError(f"Hora inválida: {hora}")
        if minuto < 0 or minuto > 59:
            raise ValueError(f"Minuto inválido: {minuto}")
        
        return hora * 60 + minuto
    
    raise ValueError(f"Formato de horário não reconhecido: {horario_str}")


@ocr_bp.route('/debug/imagens', methods=['GET'])
def listar_imagens_debug():
    """Lista todas as imagens de debug disponíveis"""
    import os
    
    debug_path = os.path.join(os.getcwd(), 'debug_ocr')
    
    print(f"[DEBUG] Pasta debug_ocr: {debug_path}")
    print(f"[DEBUG] Pasta existe? {os.path.exists(debug_path)}")
    
    if not os.path.exists(debug_path):
        os.makedirs(debug_path, exist_ok=True)
        return jsonify({'imagens': [], 'debug_path': debug_path})
    
    arquivos = []
    for filename in sorted(os.listdir(debug_path), reverse=True):
        filepath = os.path.join(debug_path, filename)
        
        if filename.endswith(('.png', '.txt')) and os.path.isfile(filepath):
            # Calcular tamanho do arquivo
            tamanho = os.path.getsize(filepath)
            
            arquivos.append({
                'nome': filename,
                'url': f'/ocr/debug/imagem/{filename}',
                'tipo': 'imagem' if filename.endswith('.png') else 'texto',
                'tamanho': tamanho
            })
    
    print(f"[DEBUG] Total de arquivos encontrados: {len(arquivos)}")
    
    return jsonify({
        'imagens': arquivos[:30],  # Últimas 30
        'total': len(arquivos),
        'debug_path': debug_path
    })

@ocr_bp.route('/debug/imagem/<filename>', methods=['GET'])
def ver_imagem_debug(filename: str):
    """Retorna uma imagem de debug específica"""
    import os
    
    debug_path = os.path.join(os.getcwd(), 'debug_ocr')
    filepath = os.path.join(debug_path, filename)
    
    print(f"[DEBUG] Tentando abrir: {filepath}")
    print(f"[DEBUG] Arquivo existe? {os.path.exists(filepath)}")
    
    if not os.path.exists(filepath):
        return jsonify({'erro': 'Arquivo não encontrado', 'path': filepath}), 404
    
    if filename.endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    # Para imagens PNG
    return send_file(filepath, mimetype='image/png')

@ocr_bp.route('/test-area/<serial>', methods=['POST'])
def testar_area(serial: str):
    """Endpoint para testar diferentes áreas de captura"""
    try:
        data = request.json
        area = data.get('area', { # type: ignore
            'x1': 0,
            'y1': 0,
            'x2': 500,
            'y2': 500
        })
        
        print(f"\n[TEST AREA] Testando área: {area}")
        
        # Capturar screenshot completo primeiro
        cmd = f'adb -s {serial} exec-out screencap -p'
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, timeout=10)
        
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Abrir imagem completa
        img_completa = Image.open(io.BytesIO(result.stdout))
        width, height = img_completa.size
        
        print(f"[TEST AREA] Resolução da tela: {width}x{height}")
        
        # Criar cópia com retângulo desenhado
        img_com_box = img_completa.copy()
        draw = ImageDraw.Draw(img_com_box)
        
        # Desenhar retângulo vermelho na área
        draw.rectangle(
            [(area['x1'], area['y1']), (area['x2'], area['y2'])],
            outline='red',
            width=5
        )
        
        # Adicionar texto com coordenadas
        texto = f"Area: ({area['x1']},{area['y1']}) -> ({area['x2']},{area['y2']})"
        draw.text((10, 10), texto, fill='red')
        
        # Salvar imagem com box
        debug_path = os.path.join(os.getcwd(), 'debug_ocr')
        os.makedirs(debug_path, exist_ok=True)
        
        timestamp = int(time.time() * 1000)
        box_path = os.path.join(debug_path, f'{timestamp}_area_teste.png')
        img_com_box.save(box_path)
        
        # Fazer crop da área
        img_crop = img_completa.crop((area['x1'], area['y1'], area['x2'], area['y2']))
        crop_path = os.path.join(debug_path, f'{timestamp}_crop_teste.png')
        img_crop.save(crop_path)
        
        return jsonify({
            'sucesso': True,
            'resolucao_tela': {'width': width, 'height': height},
            'area_testada': area,
            'imagem_com_box': f'/ocr/debug/imagem/{timestamp}_area_teste.png',
            'imagem_crop': f'/ocr/debug/imagem/{timestamp}_crop_teste.png'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'traceback': traceback.format_exc()
        }), 500