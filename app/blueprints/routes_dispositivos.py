from __future__ import annotations

import subprocess

from flask import Blueprint, flash, jsonify, redirect, request, session, url_for

from core.facade import core

bp_dispositivos = Blueprint("dispositivos", __name__)


def _require_login():
    if not session.get("logado"):
        return redirect(url_for("auth.login"))
    return None


@bp_dispositivos.route("/adicionar_dispositivo", methods=["POST"])
def adicionar_dispositivo():
    if (r := _require_login()) is not None:
        return r
    ip = (request.form.get("ip") or "").strip()
    porta = (request.form.get("porta") or "").strip()
    if not ip or not porta:
        flash("Informe IP e porta.", "warning")
        return redirect(url_for("emuladores.gerenciar_emuladores"))
    addr = f"{ip}:{porta}"
    try:
        # Requer 'adb' no PATH
        out = subprocess.run(["adb", "connect", addr], capture_output=True, text=True, timeout=15)
        if out.returncode == 0 and "connected" in (out.stdout + out.stderr).lower():
            flash(f"Dispositivo {addr} conectado.", "success")
        else:
            flash(f"Falha ao conectar {addr}: {out.stdout or out.stderr}", "danger")
    except Exception as e:
        flash(f"Erro ao conectar {addr}: {e}", "danger")
    return redirect(url_for("emuladores.gerenciar_emuladores"))


@bp_dispositivos.route("/conectar_dispositivo", methods=["POST"])
def conectar_dispositivo():
    if (r := _require_login()) is not None:
        return r
    serial = (request.form.get("serial") or "").strip()
    if not serial:
        flash("Informe o serial do dispositivo.", "warning")
        return redirect(url_for("emuladores.gerenciar_emuladores"))
    try:
        # Apenas valida se o serial existe (seta no adapter)
        core.ocr.adb.connect()
        core.ocr.adb.set_device_by_serial(serial)
        flash(f"Dispositivo {serial} selecionado.", "success")
    except Exception as e:
        flash(f"Erro ao selecionar {serial}: {e}", "danger")
    return redirect(url_for("emuladores.gerenciar_emuladores"))


@bp_dispositivos.route("/executar", methods=["POST"])
def executar():
    if (r := _require_login()) is not None:
        return r
    serial = (request.form.get("serial") or "").strip()
    comando = (request.form.get("comando") or "").strip()
    if not serial or not comando:
        flash("Informe serial e comando.", "warning")
        return redirect(url_for("emuladores.gerenciar_emuladores"))
    try:
        core.ocr.adb.connect()
        core.ocr.adb.set_device_by_serial(serial)
        saida = core.ocr.adb.shell(comando)
        flash(f"Executado '{comando}' em {serial}:\n{saida}", "info")
    except Exception as e:
        flash(f"Erro ao executar no {serial}: {e}", "danger")
    return redirect(url_for("emuladores.gerenciar_emuladores"))


@bp_dispositivos.route("/ocr/<path:serial>", methods=["POST"])
def ocr_dispositivo(serial: str):
    if (r := _require_login()) is not None:
        return r
    try:
        texto = core.ocr.ocr_text_from_serial(serial)
        return jsonify({"serial": serial, "texto": texto})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
