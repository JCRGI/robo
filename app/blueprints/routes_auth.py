from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

bp_auth = Blueprint("auth", __name__)


@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario") or ""
        senha = request.form.get("senha") or ""
        # TODO: substituir por validação real (config/DB)
        if usuario and senha:
            session["logado"] = True
            flash(f"Bem-vindo, {usuario}!", "success")
            return redirect(url_for("emuladores.gerenciar_emuladores"))
        flash("Credenciais inválidas.", "danger")
    return render_template("login.html")


@bp_auth.route("/logout")
def logout():
    session.clear()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("auth.login"))
