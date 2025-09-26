from __future__ import annotations
from flask import Blueprint, request, render_template, redirect, url_for, session, flash
import os

bp_auth = Blueprint("auth", __name__)

SIMPLE_PASSWORD = os.getenv("APP_PASSWORD", "1234")  # troque aqui ou use variável de ambiente


@bp_auth.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logado"):
        return redirect(url_for("emuladores.gerenciar_emuladores"))
    if request.method == "POST":
        entrada = (request.form.get("senha") or "").strip()
        if entrada == SIMPLE_PASSWORD:
            session["logado"] = True
            return redirect(url_for("emuladores.gerenciar_emuladores"))
        flash("Senha incorreta.", "danger")
    return render_template("login.html")


@bp_auth.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
