import os
import shutil
import threading
import time
import uuid

progresso_tarefas = {}


def duplicar_avd_em_background(avd_origem, avd_destino):
    task_id = str(uuid.uuid4())
    progresso_tarefas[task_id] = {"status": "iniciando", "percent": 0}
    print(f"[{task_id}] Iniciando duplicação de {avd_origem} para {avd_destino}")

    def tarefa():
        try:
            base_path = os.path.expanduser(f"~/.android/avd/{avd_origem}.avd")
            base_ini = os.path.expanduser(f"~/.android/avd/{avd_origem}.ini")
            nova_path = os.path.expanduser(f"~/.android/avd/{avd_destino}.avd")
            nova_ini = os.path.expanduser(f"~/.android/avd/{avd_destino}.ini")

            print(f"[{task_id}] Copiando arquivos...")
            progresso_tarefas[task_id]["status"] = "copiando arquivos"
            shutil.copytree(base_path, nova_path)
            progresso_tarefas[task_id]["percent"] = 60

            time.sleep(1)

            with open(base_ini, "r") as f:
                conteudo = f.read().replace(avd_origem, avd_destino)

            with open(nova_ini, "w") as f:
                f.write(conteudo)

            progresso_tarefas[task_id]["percent"] = 100
            progresso_tarefas[task_id]["status"] = "concluido"
            print(f"[{task_id}] Duplicação concluída.")
        except Exception as e:
            print(f"[{task_id}] ERRO: {e}")
            progresso_tarefas[task_id]["status"] = "erro"
            progresso_tarefas[task_id]["erro"] = str(e)

    threading.Thread(target=tarefa).start()
    return task_id


def obter_status(task_id):
    return progresso_tarefas.get(task_id, {"status": "desconhecido", "percent": 0})
