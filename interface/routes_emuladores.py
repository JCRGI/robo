import os
import shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from core.duplicador_avd import duplicar_avd_em_background, obter_status
from core.emulador_manager import (
    listar_avds,
    listar_emuladores_ativos,
    iniciar_emulador,
    parar_emulador,
    deletar_avd
)

from core.robo_sequencial import start_single_click_once

from core.image_processor import process_image
from core.adb_manager import AdbManager
import re

from flask import jsonify
from core.emulador_manager import duplicar_avd
from core.adb_manager import AdbManager
from core.detector_template import encontrar_botao_por_template

bp_emuladores = Blueprint("emuladores", __name__)


def limpar_nome_avd(nome):
    nome_limpo = nome.strip().replace(" ", "_")
    return re.sub(r'[^a-zA-Z0-9._-]', '', nome_limpo)


@bp_emuladores.route("/ocr/<int:porta>", methods=["POST"])
def ocr_emulador(porta):
    serial = f"emulator-{porta}"
    adb = AdbManager()
    try:
        adb.connect_device()
        # Conecta ao dispositivo correto pela porta
        adb.device = next(d for d in adb.client.devices() if d.serial == serial)
        filename = f"screenshot_{porta}.png"
        adb.capture_screen(filename)
        texto = process_image(filename)
        flash(f"OCR do AVD '{serial}':\n{texto}", "info")
    except Exception as e:
        flash(f"Erro ao fazer OCR no AVD '{serial}': {e}", "danger")

    return redirect(url_for("emuladores.gerenciar_emuladores"))

@bp_emuladores.route("/duplicar_avd", methods=["POST"])
def duplicar_avd_route():
    nome_base = request.form.get("avd_base")
    nome_novo = request.form.get("avd_novo")

    if not nome_base or not nome_novo:
        return jsonify({"erro": "Informe o AVD base e o novo nome."}), 400

    # Sanitização
    nome_novo = nome_novo.strip().replace(" ", "_")
    nome_novo = re.sub(r'[^a-zA-Z0-9._-]', '', nome_novo)

    home_dir = os.path.expanduser("~")
    avd_dir = os.path.join(home_dir, ".android", "avd")
    base_avd_path = os.path.join(avd_dir, f"{nome_base}.avd")
    base_ini_path = os.path.join(avd_dir, f"{nome_base}.ini")
    novo_avd_path = os.path.join(avd_dir, f"{nome_novo}.avd")
    novo_ini_path = os.path.join(avd_dir, f"{nome_novo}.ini")

    if not os.path.exists(base_avd_path) or not os.path.exists(base_ini_path):
        return jsonify({"erro": f"O AVD base '{nome_base}' não foi encontrado."}), 400

    if os.path.exists(novo_avd_path) or os.path.exists(novo_ini_path):
        return jsonify({"erro": f"O AVD '{nome_novo}' já existe."}), 400

    try:
        task_id = duplicar_avd_em_background(nome_base, nome_novo)
        return jsonify({"task_id": task_id})
    except Exception as e:
        return jsonify({"erro": f"Erro ao iniciar duplicação: {str(e)}"}), 500

@bp_emuladores.route("/status/<task_id>")
def status_duplicacao(task_id):
    return jsonify(obter_status(task_id))


@bp_emuladores.route("/emuladores", methods=["GET", "POST"])
def gerenciar_emuladores():

    if not session.get("logado"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        acao = request.form.get("acao")
        nome_raw = request.form.get("nome_avd") or request.form.get("avd_existente")
        porta = int(request.form.get("porta") or request.form.get("porta_existente"))

        nome_limpo = limpar_nome_avd(nome_raw)

        avds_existentes = [limpar_nome_avd(avd) for avd in listar_avds()]
        if nome_limpo in avds_existentes and acao == "criar":
            flash(f"Já existe um AVD com o nome '{nome_raw}'.", "danger")
            return redirect(url_for("emuladores.gerenciar_emuladores"))

        try:
            if acao in ["criar", "usar_existente"]:
                iniciar_emulador(nome_raw, porta)
                flash(f"Emulador '{nome_raw}' iniciado na porta {porta}.", "success")
        except Exception as e:
            flash(str(e), "danger")

        return redirect(url_for("emuladores.gerenciar_emuladores"))

    avds_disponiveis = listar_avds()
    emuladores_ativos = listar_emuladores_ativos()

    # Monta lista com status
    avds = []
    for i, avd in enumerate(avds_disponiveis):
        porta = 5560 + i
        serial = f"emulator-{porta}"
        status = "Rodando" if serial in emuladores_ativos else "Desligado"
        avds.append({
            "nome": avd,
            "porta": porta,
            "status": status
        })

    return render_template("emuladores.html", avds=avds)


@bp_emuladores.route("/parar/<int:porta>", methods=["POST"])
def parar_avd_route(porta):
    serial = f"emulator-{porta}"  # converte a porta para o serial esperado
    parar_emulador(serial)
    flash(f"Emulador na porta {porta} foi desligado.", "success")
    return redirect(url_for("emuladores.gerenciar_emuladores"))

@bp_emuladores.route("/deletar_avd/<nome>", methods=["POST"])
def deletar_avd_route(nome):
    try:
        # Para antes de deletar
        serial = f"emulator-{5560 + listar_avds().index(nome)}"
        parar_emulador(serial)
    except:
        pass  # ignora erro se já estiver parado

    try:
        deletar_avd(nome)
        flash(f"AVD '{nome}' deletado.", "info")
    except Exception as e:
        flash(str(e), "danger")

    return redirect(url_for("emuladores.gerenciar_emuladores"))

@bp_emuladores.route("/trocar_robo", methods=["POST"])
def trocar_robo():
    nome = request.form.get("avd")
    modo = request.form.get("modo")

    # Carrega lista atual
    emuladores = listar_emuladores_ativos()
    # Atualiza o robô do emulador
    for e in emuladores:
        if e == nome:
            # Aqui você pode adicionar lógica para associar um robo1/robo2
            break

    # Redireciona
    return redirect(url_for("emuladores.gerenciar_emuladores"))

def gerenciar_emuladores():
    if not session.get("logado"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        acao = request.form.get("acao")
        nome = request.form.get("nome_avd") or request.form.get("avd_existente")
        porta = int(request.form.get("porta") or request.form.get("porta_existente"))

        try:
            if acao == "criar" or acao == "usar_existente":
                iniciar_emulador(nome, porta)
                flash(f"Emulador '{nome}' iniciado na porta {porta}.", "success")
        except Exception as e:
            flash(str(e), "danger")

        return redirect(url_for("emuladores.gerenciar_emuladores"))

    avds_disponiveis = listar_avds()
    emuladores_ativos = listar_emuladores_ativos()

    # Associa status aos AVDs
    avds = []
    for i, avd in enumerate(avds_disponiveis):
        porta = 5560 + i
        serial = f"emulator-{porta}"
        status = "Rodando" if serial in emuladores_ativos else "Desligado"
        avds.append({
            "nome": avd,
            "porta": porta,
            "status": status
        })
    return render_template("emuladores.html", avds=avds)

@bp_emuladores.route("/clicar_por_texto/<int:porta>", methods=["POST"])
def clicar_por_texto(porta):
    texto = request.form.get("texto")
    if not texto:
        flash("Texto alvo não informado.", "warning")
        return redirect(url_for("emuladores.gerenciar_emuladores"))

    serial = f"emulator-{porta}"
    adb = AdbManager()
    try:
        adb.connect_device()
        adb.device = next(d for d in adb.client.devices() if d.serial == serial)

        filename = f"screenshot_{porta}.png"
        adb.capture_screen(filename)

        from core.image_processor import encontrar_texto_com_posicao
        info = encontrar_texto_com_posicao(filename, texto)

        if not info:
            flash(f"Texto '{texto}' não encontrado na tela.", "danger")
        else:
            x, y = info["x"], info["y"]
            adb.run_shell(f"input tap {x} {y}")
            print(f"Clique em '{texto}' realizado na posição ({x}, {y})", "success")

    except Exception as e:
        flash(f"Erro ao clicar: {e}", "danger")

    return redirect(url_for("emuladores.gerenciar_emuladores"))

@bp_emuladores.route("/buscar_purchase/<int:porta>", methods=["POST"])
def buscar_botao_purchase(porta):
    serial = f"emulator-{porta}"
    adb = AdbManager()

    try:
        adb.connect_device()
        adb.device = next(d for d in adb.client.devices() if d.serial == serial)
        from core.image_processor import encontrar_texto_com_posicao

        tentativas = 10
        encontrou = False

        for i in range(tentativas):
            print(f"[{serial}] Tentativa {i + 1}/{tentativas}")
            filename = f"screenshot_{serial}.png"
            adb.capture_screen(filename)

            info = encontrar_texto_com_posicao(filename, "Purchase")
            if info:
                x, y = info["x"], info["y"]
                adb.run_shell(f"input tap {x} {y}")
                flash(f"Botão 'Purchase' encontrado e clicado em ({x}, {y})!", "success")
                encontrou = True
                break
            else:
                # Ação de navegação: scroll para baixo
                adb.run_shell("input swipe 300 1000 300 500")
                time.sleep(1.5)

        if not encontrou:
            flash("Não foi possível encontrar o botão 'Purchase' após percorrer o app.", "danger")

    except Exception as e:
        flash(f"Erro durante busca automática: {e}", "danger")

    return redirect(url_for("emuladores.gerenciar_emuladores"))


@bp_emuladores.route("/clicar_template/<int:porta>", methods=["POST"])
def clicar_template(porta):
    serial = f"emulator-{porta}"
    adb = AdbManager()
    try:
        adb.connect_device()
        adb.device = next(d for d in adb.client.devices() if d.serial == serial)

        # 1) Captura a tela
        screenshot = f"screenshot_{porta}.png"
        adb.capture_screen(screenshot)

        # 2) Caminho do template (ajuste conforme sua pasta):
        # Ex.: coloque seu recorte em "<raiz do projeto>/assets/templates/btn_alvo.png"
        raiz = current_app.root_path  # diretório do app Flask
        path_template = os.path.join(raiz, "assets", "templates", "btn_alvo.png")

        # 3) Detecta por template
        match = encontrar_botao_por_template(
            path_screenshot=screenshot,
            path_template=path_template,
            conf=0.82,  # ajuste fino depois
        )

        if not match:
            flash("Botão não encontrado com confiança suficiente.", "warning")
        else:
            adb.tap(match["cx"], match["cy"])
            flash(
                f"Clique em ({int(match['cx'])}, {int(match['cy'])}) "
                f"[score={match['score']:.2f}].",
                "success",
            )
    except Exception as e:
        flash(f"Erro ao clicar no botão: {e}", "danger")

    return redirect(url_for("emuladores.gerenciar_emuladores"))

