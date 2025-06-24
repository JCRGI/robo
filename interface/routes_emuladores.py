from flask import Blueprint, render_template, request, redirect, url_for, flash, session
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
        flash("Informe os dois nomes para duplicação.", "warning")
        return redirect(url_for("emuladores.gerenciar_emuladores"))

    try:
        duplicar_avd(nome_base, nome_novo)
        flash(f"AVD '{nome_novo}' criado com base em '{nome_base}'.", "success")
    except Exception as e:
        flash(str(e), "danger")

    return redirect(url_for("emuladores.gerenciar_emuladores"))

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
        status = "Rodando" if any(e['serial'] == serial for e in emuladores_ativos) else "Desligado"
        avds.append({
            "nome": avd,
            "porta": porta,
            "status": status
        })

    return render_template("emuladores.html", avds=avds)

@bp_emuladores.route("/parar/<int:porta>", methods=["POST"])
def parar_avd_route(porta):
    parar_emulador(porta)
    flash(f"Emulador na porta {porta} foi desligado.", "success")
    return redirect(url_for("emuladores.gerenciar_emuladores"))

@bp_emuladores.route("/deletar_avd/<nome>", methods=["POST"])
def deletar_avd_route(nome):
    deletar_avd(nome)
    flash(f"AVD '{nome}' deletado.", "info")
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
        status = "Rodando" if any(e['serial'] == serial for e in emuladores_ativos) else "Desligado"
        avds.append({
            "nome": avd,
            "porta": porta,
            "status": status
        })

    return render_template("emuladores.html", avds=avds)
