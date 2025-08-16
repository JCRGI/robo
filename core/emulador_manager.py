import subprocess
import json
import os
import time
import shutil
import platform
import stat


EMULADORES_PATH = "emuladores.json"
SDK_PATH = os.environ.get("ANDROID_HOME") or "C:\\Users\\Dev\\AppData\\Local\\Android\\Sdk"
JAVA_HOME = "C:\\Program Files\\Java\\jdk-23"

def _get_env():
    env = os.environ.copy()
    env["JAVA_HOME"] = JAVA_HOME
    return env

def _get_path(tool):
    return os.path.join(SDK_PATH, "cmdline-tools", "latest", "bin", f"{tool}.bat")

def carregar_emuladores():
    if not os.path.exists(EMULADORES_PATH):
        return []
    with open(EMULADORES_PATH, "r") as f:
        return json.load(f)

def salvar_emuladores(lista):
    with open(EMULADORES_PATH, "w") as f:
        json.dump(lista, f, indent=4)

def listar_avds():
    try:
        output = subprocess.check_output(["emulator", "-list-avds"], encoding="utf-8")
        return output.strip().splitlines()
    except Exception:
        return []

def listar_emuladores_ativos():
    try:
        output = subprocess.check_output(["adb", "devices"], encoding="utf-8")
        lines = output.strip().splitlines()[1:]
        return [line.split()[0] for line in lines if "emulator" in line]
    except Exception:
        return []

def criar_novo_avd(nome_avd):
    avdmanager = _get_path("avdmanager")
    sdkmanager = _get_path("sdkmanager")
    package = "system-images;android-35;google_apis_playstore;x86_64"
    device_name = "pixel"

    env = _get_env()

    # Instalar imagem se necessário
    subprocess.run([sdkmanager, package], shell=True, env=env)

    # Criar novo AVD
    subprocess.run([
        avdmanager, "create", "avd",
        "-n", nome_avd,
        "-k", package,
        "-d", device_name,
        "--force"
    ], shell=True, env=env)

def iniciar_emulador(nome_avd, porta, modo_janela=True):
    import subprocess
    import time

    if nome_avd not in listar_avds():
        criar_novo_avd(nome_avd)

    cmd = [
        "emulator", "-avd", nome_avd,
        "-port", str(porta)
    ]
    if not modo_janela:
        cmd += ["-no-audio", "-no-window"]

    subprocess.Popen(cmd)
    time.sleep(3)  # pequena espera antes de checar o status

    serial = f"emulator-{porta}"

    # Aguarda o emulador aparecer com status 'device'
    for _ in range(30):
        try:
            output = subprocess.check_output(["adb", "devices"], encoding="utf-8")
            linhas = [l.strip() for l in output.strip().splitlines() if l.strip()]
            for linha in linhas[1:]:
                if serial in linha and "device" in linha:
                    print(f"[OK] {serial} conectado ao ADB.")
                    raise StopIteration
        except StopIteration:
            break
        time.sleep(1)
    else:
        print(f"[ERRO] Timeout: {serial} não ficou online.")
        return

    # Aguarda o Android terminar o boot completo
    for _ in range(30):  # até 30 segundos
        try:
            boot_status = subprocess.check_output(["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"], encoding="utf-8").strip()
            if boot_status == "1":
                print(f"[OK] {serial} terminou o boot.")
                break
        except:
            pass
        time.sleep(1)
    else:
        print(f"[ERRO] Timeout: {serial} não completou o boot.")
        return

    # 🟢 Agora o sistema está pronto para abrir o app
    pacote = "com.disney.wdw.android"
    try:
        subprocess.run([
            "adb", "-s", serial,
            "shell", "monkey",
            "-p", pacote,
            "-c", "android.intent.category.LAUNCHER",
            "1"
        ])
        print(f"[OK] App {pacote} aberto automaticamente em {serial}")
    except Exception as e:
        print(f"[ERRO] Ao abrir app {pacote}: {e}")
        return

    # 🤖 Robô automático: busca botão "Purchase"
    try:
        esperar_home_e_clicar_purchase(serial)
    except Exception as e:
        print(f"[ERRO] Falha na automação com OCR inteligente: {e}")
        
        
        
        
        

def parar_emulador(serial):
    subprocess.run(["adb", "-s", serial, "emu", "kill"])
    # Aguarda até que o dispositivo realmente suma da lista
    for _ in range(10):  # tenta por até 10 x 0.5 = 5 segundos
        time.sleep(0.5)
        ativos = listar_emuladores_ativos()
        if serial not in ativos:
            break

def deletar_avd(nome_avd):
    avd_dir = os.path.expanduser(f"~/.android/avd/{nome_avd}.avd")
    ini_file = os.path.expanduser(f"~/.android/avd/{nome_avd}.ini")

    def handle_remove_readonly(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    try:
        if os.path.exists(avd_dir):
            shutil.rmtree(avd_dir, onerror=handle_remove_readonly)
        if os.path.exists(ini_file):
            os.remove(ini_file)
    except Exception as e:
        raise Exception(f"Erro ao deletar AVD '{nome_avd}': {e}")


    def listar_emuladores_ativos():
        try:
            output = subprocess.check_output(["adb", "devices"], encoding="utf-8")
            lines = output.strip().splitlines()[1:]

            emuladores = []
            for line in lines:
                if "emulator-" in line:
                    serial = line.split()[0]
                    port = serial.replace("emulator-", "")
                    emuladores.append({
                        "serial": serial,
                        "porta": int(port),
                        "status": "rodando"
                    })
            return emuladores
        except Exception:
            return []
        

  

def duplicar_avd(nome_base: str, nome_novo: str):
    home_dir = os.path.expanduser("~")
    avd_dir = os.path.join(home_dir, ".android", "avd")

    origem_avd_path = os.path.join(avd_dir, f"{nome_base}.avd")
    origem_ini_path = os.path.join(avd_dir, f"{nome_base}.ini")

    destino_avd_path = os.path.join(avd_dir, f"{nome_novo}.avd")
    destino_ini_path = os.path.join(avd_dir, f"{nome_novo}.ini")

    if not os.path.exists(origem_avd_path) or not os.path.exists(origem_ini_path):
        raise Exception(f"O AVD '{nome_base}' não existe ou está incompleto.")

    if os.path.exists(destino_avd_path) or os.path.exists(destino_ini_path):
        raise Exception(f"Já existe um AVD com o nome '{nome_novo}'.")

    # Copiar diretórios e arquivos
    shutil.copytree(origem_avd_path, destino_avd_path)
    shutil.copy2(origem_ini_path, destino_ini_path)

    # Atualizar o .ini do novo AVD
    with open(destino_ini_path, 'r') as f:
        conteudo = f.read()

    novo_conteudo = conteudo.replace(f"{nome_base}.avd", f"{nome_novo}.avd").replace(nome_base, nome_novo)

    with open(destino_ini_path, 'w') as f:
        f.write(novo_conteudo)

    print(f"[OK] AVD '{nome_novo}' duplicado com base em '{nome_base}'.")
    
    


def buscar_e_clicar_purchase(serial, tentativas=12):
    from core.adb_manager import AdbManager
    from core.image_processor import encontrar_texto_com_posicao
    import time

    termos = ["purchase", "Purchase"]
    adb = AdbManager()
    adb.connect_device()
    adb.device = next(d for d in adb.client.devices() if d.serial == serial)

    for i in range(tentativas):
        print(f"\n[{serial}] Tentativa {i + 1}/{tentativas}")

        filename = f"screenshot_{serial}.png"
        adb.capture_screen(filename)

        info = encontrar_texto_com_posicao(filename, "purchase")

        if info:
            x = info["x"]
            y = info["y"]
            termo = info["texto_encontrado"]

            adb.run_shell(f"input tap {x} {y}")
            print(f"[AUTO] Clicou automaticamente em '{termo.upper()}' na posição ({x}, {y}) ✅")
            return True

        print("[INFO] Termo não encontrado, realizando scroll...")
        adb.run_shell("input swipe 200 800 200 300")
        time.sleep(2)

    print(f"[ERRO] Nenhum botão correspondente a {termos} foi encontrado após {tentativas} tentativas.")
    return False


def esperar_home_e_clicar_purchase(serial, timeout=60):
    from core.adb_manager import AdbManager
    from core.image_processor import encontrar_texto_com_posicao
    import time

    adb = AdbManager()
    adb.connect_device()
    adb.device = next(d for d in adb.client.devices() if d.serial == serial)

    print(f"[{serial}] Aguardando a tela de home carregar...")

    inicio = time.time()
    while time.time() - inicio < timeout:
        filename = f"screenshot_{serial}.png"
        adb.capture_screen(filename)

        info = encontrar_texto_com_posicao(filename, ["hello", "lightning", "multi pass"])
        if info:
            print(f"[{serial}] Interface detectada! ✅")
            break

        print(f"[{serial}] Ainda carregando... nova tentativa em 1.5s")
        time.sleep(1.5)
    else:
        print(f"[{serial}] ⚠️ Timeout: a tela não carregou em {timeout}s.")
        return False

    # Agora executa swipe e clique no botão
    
    print(f"[{serial}] Executando swipe curto...")
    adb.run_shell("input swipe 300 1000 300 200 300")
    time.sleep(1.5)

    print(f"[{serial}] Procurando botão 'Purchase' após o swipe...")

    from core.image_processor import encontrar_texto_com_posicao
    texto = "purchase"
    info = encontrar_texto_com_posicao(filename, texto)

    if not info:
        print(f"Texto '{texto}' não encontrado na tela.", "danger")
        return False
    else:
        x, y = info["x"], info["y"]
        adb.run_shell(f"input tap {x} {y}")
        print(f"Clique em '{texto}' realizado na posição ({x}, {y})", "success")
        return True