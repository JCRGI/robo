import subprocess
import re

def logar_toques(serial):
    print(f"[TOUCH LOGGER] Iniciando captura de eventos de toque do {serial}...\n")
    
    process = subprocess.Popen(
        ["adb", "-s", serial, "shell", "getevent", "-lt"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    x = y = None

    try:
        for line in process.stdout:
            if "ABS_MT_POSITION_X" in line:
                x = int(line.split()[-1], 16)
            elif "ABS_MT_POSITION_Y" in line:
                y = int(line.split()[-1], 16)
            elif "SYN_REPORT" in line and x is not None and y is not None:
                print(f"[TOQUE] Coordenadas detectadas: x={x} y={y}")
                x = y = None
    except KeyboardInterrupt:
        print("[TOUCH LOGGER] Interrompido.")
        process.terminate()
