from __future__ import annotations
from flask import Blueprint, request, jsonify, session, abort

from core.facade import core
from core.utils import normalizar_porta_console

bp_bots = Blueprint("bots", __name__)

def _auth():
    if not session.get("logado"):
        abort(401)

def _json():
    data = request.get_json(silent=True)
    if data is None:
        abort(400, description="JSON inválido ou ausente (Content-Type: application/json).")
    return data

@bp_bots.route("/bots/start", methods=["POST"])
def start_bot():
    _auth()
    data = _json()
    porta_raw = data.get("porta")
    try:
        porta = int(porta_raw)
    except (TypeError, ValueError):
        abort(400, description="Porta inválida.")
    texto = (data.get("texto_alvo") or "").strip()
    if not texto:
        abort(400, description="texto_alvo obrigatório.")
    novo = (data.get("novo_texto") or "").strip() or None
    intervalo = float(data.get("intervalo") or 3)
    notify = bool(data.get("notify_whatsapp"))
    serial = f"emulator-{normalizar_porta_console(porta)}"
    st = core.runtime_bots.start_bot(serial, texto, novo, intervalo, notify_whatsapp=notify)
    return jsonify(_status_to_dict(st))

@bp_bots.route("/bots/pause", methods=["POST"])
def pause_bot():
    _auth()
    data = _json()
    try:
        porta = int(data.get("porta"))
    except (TypeError, ValueError):
        abort(400, description="Porta inválida.")
    pause = bool(data.get("pause"))
    serial = f"emulator-{normalizar_porta_console(porta)}"
    st = core.runtime_bots.pause_bot(serial, pause)
    return jsonify(_status_to_dict(st))

@bp_bots.route("/bots/stop", methods=["POST"])
def stop_bot():
    _auth()
    data = _json()
    try:
        porta = int(data.get("porta"))
    except (TypeError, ValueError):
        abort(400, description="Porta inválida.")
    serial = f"emulator-{normalizar_porta_console(porta)}"
    st = core.runtime_bots.stop_bot(serial)
    return jsonify(_status_to_dict(st))

@bp_bots.route("/bots/status", methods=["GET"])
def list_bots():
    _auth()
    data = {k: _status_to_dict(v) for k, v in core.runtime_bots.list_status().items()}
    return jsonify(data)

def _status_to_dict(st):
    return {
        "running": st.running,
        "paused": st.paused,
        "cycles": st.cycles,
        "last_result": st.last_result,
        "serial": st.config.serial,
        "texto_alvo": st.config.texto_alvo,
        "novo_texto": st.config.novo_texto,
        "intervalo": st.config.intervalo,
    }