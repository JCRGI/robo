from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from core.facade import core
from core.tasks_bg import fire_and_forget
from core.utils import normalizar_porta_console, limpar_nome_avd

bp_emuladores = Blueprint("emuladores", __name__)

@bp_emuladores.route("/status/start_busy", methods=["GET"])
def status_start_busy():
    from core.locks import is_avd_start_busy
    return jsonify({"busy": is_avd_start_busy()})

@bp_emuladores.route("/duplicar_avd", methods=["POST"])
def duplicar_avd_route():
    nome_base = (request.form.get("avd_base") or "").strip()
    nome_novo = limpar_nome_avd(request.form.get("avd_novo") or "")
    if not nome_base or not nome_novo:
        return jsonify({"erro": "Informe o AVD base e o novo nome."}), 400
    try:
        task_id = core.clone.start(nome_base, nome_novo)
        return jsonify({"task_id": task_id})
    except Exception as e:
        return jsonify({"erro": f"Erro ao iniciar duplicação: {str(e)}"}), 500

@bp_emuladores.route("/status/<task_id>")
def status_duplicacao(task_id: str):
    return jsonify(core.clone.status(task_id))

@bp_emuladores.route("/emuladores", methods=["GET", "POST"])
def gerenciar_emuladores():
    if not session.get("logado"):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        acao = request.form.get("acao")

        # garanta tipos corretos para o type checker
        nome: str = (request.form.get("nome_avd") or request.form.get("avd_existente") or "").strip()
        porta_str: str = (request.form.get("porta") or request.form.get("porta_existente") or "").strip()
        porta_opt: int | None = int(porta_str) if porta_str else None

        try:
            if acao in ["criar", "usar_existente"]:
                if not nome:
                    flash("Informe o nome do AVD.", "warning")
                    return redirect(url_for("emuladores.gerenciar_emuladores"))
                used_port = core.emulators.start(
                    nome,
                    porta_opt,
                    pacote="com.disney.wdw.android",
                    wait=True,
                )
                serial = f"emulator-{normalizar_porta_console(used_port)}"
                fire_and_forget(core.ocr.auto_click_purchase, serial, tentativas=12, delay=1.0)
                flash(f"Emulador '{nome}' iniciado na porta {used_port}.", "success")
        except Exception as e:
            flash(str(e), "danger")
        return redirect(url_for("emuladores.gerenciar_emuladores"))

    snap = core.emulators.snapshot()
    avds = [{"nome": s.avd, "porta": s.port, "status": s.status} for s in snap]
    return render_template("emuladores.html", avds=avds)

@bp_emuladores.route("/parar/<int:porta>", methods=["POST"])
def parar_avd_route(porta: int):
    serial = f"emulator-{normalizar_porta_console(porta)}"
    try:
        core.emulators.stop(serial)
        flash(f"Emulador {serial} desligado.", "success")
    except Exception as e:
        flash(f"Falha ao desligar {serial}: {e}", "danger")
    return redirect(url_for("emuladores.gerenciar_emuladores"))

@bp_emuladores.route("/deletar_avd/<nome>", methods=["POST"])
def deletar_avd_route(nome: str):
    try:
        core.emulators.delete(nome)
        flash(f"AVD '{nome}' deletado.", "info")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("emuladores.gerenciar_emuladores"))

@bp_emuladores.route("/ligar_todos", methods=["POST"])
def ligar_todos():
    if not session.get("logado"):
        return redirect(url_for("auth.login"))

    def _job():
        try:
            for dev in core.emulators.snapshot():
                if dev.status == "Rodando":
                    continue
                try:
                    used_port = core.emulators.start(
                        dev.avd, # type: ignore
                        dev.port,
                        pacote="com.disney.wdw.android",
                        wait=True,
                    )
                    serial = f"emulator-{normalizar_porta_console(used_port)}"
                    fire_and_forget(core.ocr.auto_click_purchase, serial, tentativas=12, delay=1.0)
                except Exception as e:
                    print(f"[ligar_todos] Falha ao iniciar {dev.avd}: {e}")
        except Exception as e:
            print(f"[ligar_todos] erro: {e}")

    fire_and_forget(_job)
    flash("Ligando todos os AVDs (um por vez).", "info")
    return redirect(url_for("emuladores.gerenciar_emuladores"))

@bp_emuladores.route("/desligar_todos", methods=["POST"])
def desligar_todos():
    if not session.get("logado"):
        return redirect(url_for("auth.login"))
    try:
        for dev in core.emulators.snapshot():
            if dev.status == "Rodando":
                serial = f"emulator-{normalizar_porta_console(dev.port)}"
                try:
                    core.emulators.stop(serial)
                except Exception as e:
                    print(f"[desligar_todos] erro ao desligar {serial}: {e}")
        flash("Todos os AVDs foram desligados (quando aplicável).", "info")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("emuladores.gerenciar_emuladores"))
