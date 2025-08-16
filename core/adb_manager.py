from ppadb.client import Client as AdbClient

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
        
    def tap(self, x: int | float, y: int | float):
        if not self.device:
            raise Exception("Nenhum dispositivo conectado.")
        self.device.shell(f"input tap {int(x)} {int(y)}")
