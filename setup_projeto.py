import os

# Estrutura de pastas e arquivos com conteúdo básico
estrutura = {
    "venv": None,  # Pasta do ambiente virtual (não será criada pelo script)
    "core": {
        "adb_manager.py": """from ppadb.client import Client as AdbClient

class AdbManager:
    def __init__(self, host="127.0.0.1", port=5037):
        self.client = AdbClient(host=host, port=port)
        self.device = None

    def connect_device(self):
        devices = self.client.devices()
        if len(devices) == 0:
            raise Exception("Nenhum dispositivo conectado via ADB.")
        self.device = devices[0]
        print(f"Dispositivo conectado: {self.device.serial}")

    def run_shell(self, command):
        if not self.device:
            raise Exception("Nenhum dispositivo conectado.")
        return self.device.shell(command)

    def capture_screen(self, filename="screenshot.png"):
        if not self.device:
            raise Exception("Nenhum dispositivo conectado.")
        image = self.device.screencap()
        with open(filename, "wb") as f:
            f.write(image)
        print(f"Screenshot salva em {filename}")
""",
        "image_processor.py": """# Aqui ficará o código para visão computacional, OpenCV, etc.

def process_image(path):
    print(f"Processando imagem {path}")
""",
        "logger.py": """import logging

def get_logger(name=__name__):
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    return logging.getLogger(name)
""",
        "utils.py": """# Funções auxiliares

def exemplo_util():
    print("Função utilitária")
""",
    },
    "services": {
        "whatsapp_bot.py": """# Exemplo de automação para WhatsApp

def start_whatsapp_bot():
    print("Bot do WhatsApp iniciado")
""",
        "farm_game_bot.py": """# Exemplo de bot para jogo mobile

def start_farm_game_bot():
    print("Bot do jogo iniciado")
""",
    },
    "configs": {
        "settings.py": """# Configurações e constantes do projeto

ADB_HOST = "127.0.0.1"
ADB_PORT = 5037
"""
    },
    "tests": {
        "test_adb_manager.py": """import unittest
from core.adb_manager import AdbManager

class TestAdbManager(unittest.TestCase):
    def test_connect_no_device(self):
        adb = AdbManager()
        try:
            adb.connect_device()
        except Exception as e:
            self.assertEqual(str(e), "Nenhum dispositivo conectado via ADB.")

if __name__ == "__main__":
    unittest.main()
"""
    },
    "robo.py": """from core.adb_manager import AdbManager

def main():
    adb = AdbManager()
    adb.connect_device()
    output = adb.run_shell("echo 'Olá, mundo Android!'")
    print(output)
    adb.capture_screen()

if __name__ == "__main__":
    main()
""",
    "requirements.txt": """pure-python-adb
opencv-python
""",
    "README.md": """# Meu Robô

Projeto para automação via ADB com funcionalidades de visão computacional e IA.

## Estrutura

- core: núcleo da aplicação
- services: bots e automações específicas
- configs: configurações do projeto
- tests: testes unitários

## Como rodar

1. Crie e ative o ambiente virtual:
python -m venv venv
source venv/Scripts/activate # Windows Git Bash

2. Instale dependências:
pip install -r requirements.txt

Copiar código
3. Rode o robô:
python robo.py
""",
}


def criar_estrutura(base_path, estrutura):
    for nome, conteudo in estrutura.items():
        caminho = os.path.join(base_path, nome)
        if conteudo is None:
            # Criar pasta vazia (ex: venv)
            os.makedirs(caminho, exist_ok=True)
            print(f"Criada pasta: {caminho}")
        elif isinstance(conteudo, dict):
            # Criar pasta com arquivos/subpastas
            os.makedirs(caminho, exist_ok=True)
            print(f"Criada pasta: {caminho}")
            criar_estrutura(caminho, conteudo)
        else:
            # Criar arquivo com conteúdo
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            print(f"Criado arquivo: {caminho}")


if __name__ == "__main__":
    pasta_projeto = os.getcwd()  # pasta atual
    print(f"Criando estrutura de projeto em {pasta_projeto} ...")
    criar_estrutura(pasta_projeto, estrutura)
    print("Estrutura criada com sucesso!")
