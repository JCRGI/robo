import os


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    # Exemplos úteis ao seu projeto:
    ADB_HOST = os.getenv("ADB_HOST", "127.0.0.1")
    ADB_PORT = int(os.getenv("ADB_PORT", "5037"))
    # Se usar Tesseract no Windows:
    TESSERACT_CMD = os.getenv(
        "TESSERACT_CMD"
    )  # ex: C:\\Program Files\\Tesseract-OCR\\tesseract.exe
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False
