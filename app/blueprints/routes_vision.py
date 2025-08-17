from __future__ import annotations

import os
import uuid

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from core.facade import core

bp_vision = Blueprint("vision", __name__, url_prefix="/vision")

@bp_vision.route("/", methods=["GET"])
def page():
    return render_template("vision.html")

@bp_vision.route("/interpretar", methods=["POST"])
def interpretar():
    file = request.files.get("imagem")
    if not file or file.filename == "":
        flash("Selecione um arquivo de imagem.", "warning")
        return redirect(url_for("vision.page"))

    uid = uuid.uuid4().hex
    inst_dir = current_app.instance_path
    os.makedirs(inst_dir, exist_ok=True)
    in_path = os.path.join(inst_dir, f"upload_{uid}.png")
    out_dir = os.path.join(current_app.static_folder, "tmp") # type: ignore
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"annot_{uid}.png")

    file.save(in_path)
    try:
        results = core.vision.interpret(in_path)
        core.vision.annotate(in_path, results, out_path)
    finally:
        try:
            os.remove(in_path)
        except Exception:
            pass

    # caminho relativo para servir a imagem anotada
    rel_out = os.path.relpath(out_path, current_app.static_folder).replace("\\", "/")
    return render_template("vision.html", results=results, annotated_url=url_for("static", filename=rel_out))
