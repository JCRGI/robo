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
    if nome_avd not in listar_avds():
        criar_novo_avd(nome_avd)

    cmd = [
        "emulator", "-avd", nome_avd,
        "-port", str(porta)
    ]
    if not modo_janela:
        cmd += ["-no-audio", "-no-window"]

    subprocess.Popen(cmd)
    time.sleep(5)

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


