import os
import re
from datetime import datetime

import cv2
import pytesseract
import subprocess
import time

# Caminho do Tesseract no Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def process_image(path):
    print(f"Processando OCR da imagem: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Imagem não encontrada: {path}")

    imagem = cv2.imread(path)
    texto = pytesseract.image_to_string(imagem, lang="por")
    print("Texto reconhecido:")
    print(texto)
    return texto


def encontrar_texto_com_posicao(path, termos_procurados):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Imagem não encontrada: {path}")

    if isinstance(termos_procurados, str):
        termos_procurados = [termos_procurados]

    termos_procurados = [t.strip().lower() for t in termos_procurados]

    imagem = cv2.imread(path)

    resultados = pytesseract.image_to_data(imagem, lang="por", output_type=pytesseract.Output.DICT)

    for i in range(len(resultados["text"])):
        palavra = resultados["text"][i].strip().lower()
        x = resultados["left"][i]
        y = resultados["top"][i]
        w = resultados["width"][i]
        h = resultados["height"][i]

        for termo in termos_procurados:
            if termo in palavra:
                centro_x = x + w // 2
                centro_y = y + h // 2
                print(
                    f"[OCR] '{termo}' detectado na palavra '{palavra}' em ({centro_x}, {centro_y})"
                )
                return {"texto_encontrado": palavra, "x": centro_x, "y": centro_y}

    return None


def parse_horario(horario_str):
    """
    Converte string de horário para objeto datetime.
    Suporta múltiplos formatos.
    """
    if not horario_str:
        return None
    
    horario_str = horario_str.strip().upper()
    
    # Remover caracteres extras
    horario_str = horario_str.replace('O', '0')  # Corrigir OCR: O -> 0
    horario_str = re.sub(r'[^\d:AMP\s]', '', horario_str)  # Manter apenas dígitos, :, AM, PM, espaços
    
    print(f"[DEBUG] Tentando parsear: '{horario_str}'")
    
    # Lista de padrões (ordem importa!)
    patterns = [
        # 10:30 AM, 10:30 PM
        (r'(\d{1,2}):(\d{2})\s*(AM|PM)', lambda m: (int(m.group(1)), int(m.group(2)), m.group(3))),
        # 10:30AM, 10:30PM (sem espaço)
        (r'(\d{1,2}):(\d{2})(AM|PM)', lambda m: (int(m.group(1)), int(m.group(2)), m.group(3))),
        # 1030 AM, 1030 PM
        (r'(\d{2})(\d{2})\s*(AM|PM)', lambda m: (int(m.group(1)), int(m.group(2)), m.group(3))),
        # 10:30 (24 horas)
        (r'(\d{1,2}):(\d{2})$', lambda m: (int(m.group(1)), int(m.group(2)), None)),
        # 1030 (24 horas, sem :)
        (r'^(\d{2})(\d{2})$', lambda m: (int(m.group(1)), int(m.group(2)), None)),
    ]
    
    for pattern, parser in patterns:
        match = re.search(pattern, horario_str)
        if match:
            try:
                hora, minuto, periodo = parser(match)
                
                # Validar hora e minuto
                if not (0 <= hora <= 23 and 0 <= minuto <= 59):
                    continue
                
                # Converter AM/PM para 24h
                if periodo:
                    if periodo == 'PM' and hora != 12:
                        hora += 12
                    elif periodo == 'AM' and hora == 12:
                        hora = 0
                
                # Criar datetime
                result = datetime.strptime(f"{hora:02d}:{minuto:02d}", "%H:%M")
                print(f"[DEBUG] ✅ Parseado: {hora:02d}:{minuto:02d}")
                return result
                
            except (ValueError, AttributeError) as e:
                print(f"[DEBUG] ⚠️ Erro no parse: {e}")
                continue
    
    print(f"[DEBUG] ❌ Nenhum padrão correspondeu")
    return None


def encontrar_horarios_menores(path, horario_referencia):
    """
    Busca na imagem por horários menores que o horário de referência.
    """
    print(f"\n{'='*70}")
    print(f"🕒 BUSCANDO HORÁRIOS MENORES QUE: {horario_referencia}")
    print(f"{'='*70}")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Imagem não encontrada: {path}")
    
    ref_time = parse_horario(horario_referencia)
    if ref_time is None:
        raise ValueError(f"Formato de horário inválido: {horario_referencia}")
    
    print(f"✅ Horário de referência parseado: {ref_time.strftime('%H:%M')}")
    
    imagem = cv2.imread(path)
    resultados = pytesseract.image_to_data(
        imagem, 
        lang="por+eng",
        output_type=pytesseract.Output.DICT
    )
    
    horarios_encontrados = []
    horario_pattern = r'\d{1,2}:?\d{2}\s?(?:AM|PM|am|pm)?'
    
    for i in range(len(resultados["text"])):
        texto = resultados["text"][i].strip()
        confianca = int(resultados["conf"][i])
        
        if confianca < 50 or not texto:
            continue
        
        matches = re.finditer(horario_pattern, texto, re.IGNORECASE)
        
        for match in matches:
            horario_str = match.group(0)
            horario_parsed = parse_horario(horario_str)
            
            if horario_parsed is None:
                continue
            
            if horario_parsed < ref_time:
                x = resultados["left"][i]
                y = resultados["top"][i]
                w = resultados["width"][i]
                h = resultados["height"][i]
                
                centro_x = x + w // 2
                centro_y = y + h // 2
                
                horario_info = {
                    "horario": horario_str,
                    "horario_parsed": horario_parsed,
                    "x": centro_x,
                    "y": centro_y,
                    "confianca": confianca,
                    "diferenca_minutos": int((ref_time - horario_parsed).total_seconds() / 60)
                }
                
                horarios_encontrados.append(horario_info)
                
                print(f"✅ Horário menor encontrado:")
                print(f"   Texto: {horario_str}")
                print(f"   Parseado: {horario_parsed.strftime('%H:%M')}")
                print(f"   Posição: ({centro_x}, {centro_y})")
                print(f"   Confiança: {confianca}%")
    
    horarios_encontrados.sort(key=lambda x: x["horario_parsed"], reverse=True)
    
    print(f"\n{'='*70}")
    print(f"📊 RESULTADO: {len(horarios_encontrados)} horário(s) menor(es) encontrado(s)")
    print(f"{'='*70}\n")
    
    return horarios_encontrados


def encontrar_horario_mais_proximo(path, horario_referencia):
    """
    Encontra o horário mais próximo (menor) ao horário de referência.
    """
    horarios = encontrar_horarios_menores(path, horario_referencia)
    
    if not horarios:
        print("⚠️  Nenhum horário menor encontrado")
        return None
    
    mais_proximo = horarios[0]
    
    print(f"🎯 HORÁRIO MAIS PRÓXIMO:")
    print(f"   {mais_proximo['horario']} em ({mais_proximo['x']}, {mais_proximo['y']})")
    print(f"   {mais_proximo['diferenca_minutos']} minutos antes da referência")
    
    return mais_proximo


def visualizar_horarios_detectados(path, horario_referencia, output_path=None):
    """
    Cria imagem com horários detectados marcados.
    """
    horarios = encontrar_horarios_menores(path, horario_referencia)
    
    if not horarios:
        print("⚠️  Nenhum horário para visualizar")
        return
    
    imagem = cv2.imread(path)
    
    for i, h in enumerate(horarios):
        cor = (0, 255, 0) if i == 0 else (0, 165, 255)
        cv2.circle(imagem, (h["x"], h["y"]), 10, cor, 2)
        
        texto = f"{h['horario']} (-{h['diferenca_minutos']}min)"
        cv2.putText(imagem, texto, (h["x"] + 15, h["y"]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)
    
    if output_path:
        cv2.imwrite(output_path, imagem)
        print(f"✅ Imagem salva em: {output_path}")
    else:
        cv2.imshow("Horários Detectados", imagem)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def capture_screen(serial, output_path):
    """
    Captura screenshot do emulador.
    
    Args:
        serial: Serial do emulador (ex: "emulator-5560")
        output_path: Caminho para salvar a imagem
        
    Returns:
        True se sucesso, False caso contrário
    """
    try:
        # 1. Capturar para o dispositivo
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "screencap", "-p", "/sdcard/screenshot.png"],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"[ERRO] Falha ao capturar screenshot: {result.stderr.decode()}")
            return False
        
        # 2. Puxar para o PC
        result = subprocess.run(
            ["adb", "-s", serial, "pull", "/sdcard/screenshot.png", output_path],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"[ERRO] Falha ao fazer pull: {result.stderr.decode()}")
            return False
        
        # 3. Limpar do dispositivo
        subprocess.run(
            ["adb", "-s", serial, "shell", "rm", "/sdcard/screenshot.png"],
            timeout=5
        )
        
        # Verificar se arquivo foi criado
        if not os.path.exists(output_path):
            print(f"[ERRO] Arquivo não foi criado: {output_path}")
            return False
        
        print(f"[DEBUG] Screenshot salvo: {output_path}")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"[ERRO] Timeout ao capturar screenshot")
        return False
    except Exception as e:
        print(f"[ERRO] Exceção ao capturar screenshot: {e}")
        return False


def tap(serial, x, y):
    """
    Simula toque na tela.
    
    Args:
        serial: Serial do emulador (ex: "emulator-5560")
        x: Coordenada X
        y: Coordenada Y
        
    Returns:
        True se sucesso, False caso contrário
    """
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "input", "tap", str(x), str(y)],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"[ERRO] Falha ao executar tap: {result.stderr.decode()}")
            return False
        
        print(f"[DEBUG] Tap executado em ({x}, {y})")
        time.sleep(0.5)  # Delay após o toque
        return True
        
    except subprocess.TimeoutExpired:
        print(f"[ERRO] Timeout ao executar tap")
        return False
    except Exception as e:
        print(f"[ERRO] Exceção ao executar tap: {e}")
        return False


def swipe(serial, x1, y1, x2, y2, duration=300):
    """
    Simula deslizar na tela.
    
    Args:
        serial: Serial do emulador
        x1, y1: Coordenadas iniciais
        x2, y2: Coordenadas finais
        duration: Duração em ms (padrão: 300)
        
    Returns:
        True se sucesso, False caso contrário
    """
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "input", "swipe", 
             str(x1), str(y1), str(x2), str(y2), str(duration)],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"[ERRO] Falha ao executar swipe: {result.stderr.decode()}")
            return False
        
        print(f"[DEBUG] Swipe executado: ({x1},{y1}) -> ({x2},{y2})")
        time.sleep(0.5)
        return True
        
    except Exception as e:
        print(f"[ERRO] Exceção ao executar swipe: {e}")
        return False


def input_text(serial, texto):
    """
    Insere texto no campo focado.
    
    Args:
        serial: Serial do emulador
        texto: Texto a inserir
        
    Returns:
        True se sucesso, False caso contrário
    """
    try:
        # Escapar espaços e caracteres especiais
        texto_escaped = texto.replace(" ", "%s")
        
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "input", "text", texto_escaped],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"[ERRO] Falha ao inserir texto: {result.stderr.decode()}")
            return False
        
        print(f"[DEBUG] Texto inserido: {texto}")
        return True
        
    except Exception as e:
        print(f"[ERRO] Exceção ao inserir texto: {e}")
        return False


def press_key(serial, keycode):
    """
    Simula pressionar uma tecla.
    
    Args:
        serial: Serial do emulador
        keycode: Código da tecla (ex: KEYCODE_BACK, KEYCODE_HOME, etc)
        
    Returns:
        True se sucesso, False caso contrário
        
    Keycodes comuns:
        KEYCODE_BACK = 4
        KEYCODE_HOME = 3
        KEYCODE_ENTER = 66
        KEYCODE_MENU = 82
    """
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "shell", "input", "keyevent", str(keycode)],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"[ERRO] Falha ao pressionar tecla: {result.stderr.decode()}")
            return False
        
        print(f"[DEBUG] Tecla pressionada: {keycode}")
        time.sleep(0.3)
        return True
        
    except Exception as e:
        print(f"[ERRO] Exceção ao pressionar tecla: {e}")
        return False


def selecionar_horario_disponivel(serial, horario_limite="10:30 AM"):
    """
    Captura tela, encontra horários menores que o limite e clica no mais próximo.
    
    Args:
        serial: Serial do emulador
        horario_limite: Horário de referência
        
    Returns:
        True se encontrou e clicou, False caso contrário
    """
    # 🔴 CORRIGIDO: Importar gateway diretamente
    from core.gateways import emulator_ctl
    
    print(f"\n{'='*70}")
    print(f"🤖 SELECIONANDO HORÁRIO DISPONÍVEL (< {horario_limite})")
    print(f"{'='*70}")
    
    # 1. Capturar screenshot
    screenshot_path = "temp_horarios.png"
    print("\n[1/3] Capturando tela...")
    
    success = emulator_ctl.capture_screen(serial, screenshot_path)
    
    if not success or not os.path.exists(screenshot_path):
        print("❌ Falha ao capturar tela")
        return False
    
    print("✅ Tela capturada")
    
    # 2. Buscar horários menores
    print(f"\n[2/3] Buscando horários < {horario_limite}...")
    horario = encontrar_horario_mais_proximo(screenshot_path, horario_limite)
    
    if not horario:
        print("❌ Nenhum horário disponível encontrado")
        os.remove(screenshot_path)
        return False
    
    # 3. Clicar no horário
    print(f"\n[3/3] Clicando em {horario['horario']}...")
    emulator_ctl.tap(serial, horario['x'], horario['y'])
    
    print(f"\n✅ Horário {horario['horario']} selecionado!")
    
    # Limpar arquivo temporário
    os.remove(screenshot_path)
    
    return True


# Uso:
if __name__ == "__main__":
    sucesso = selecionar_horario_disponivel("emulator-5560", "10:30 AM")
    
    if sucesso:
        print("\n🎉 Horário selecionado com sucesso!")
    else:
        print("\n⚠️ Não foi possível selecionar horário")
