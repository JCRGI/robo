import os
import shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from core.duplicador_avd import duplicar_avd_em_background, obter_status
from core.emulador_manager import (
    listar_avds,
    listar_emuladores_ativos,
    iniciar_emulador,
    parar_emulador,
    deletar_avd
)
import re

from flask import jsonify
from core.emulador_manager import duplicar_avd

bp_emuladores = Blueprint("emuladores", __name__)


def limpar_nome_avd(nome):
    nome_limpo = nome.strip().replace(" ", "_")
    return re.sub(r'[^a-zA-Z0-9._-]', '', nome_limpo)

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

   
