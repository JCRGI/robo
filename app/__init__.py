from __future__ import annotations

import logging
import os

from flask import Flask, app, redirect, url_for


def create_app(config_object: str | None = None) -> Flask:
    # templates agora ficam em app/templates (padrão do Flask para pacotes)
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(SECRET_KEY=os.getenv("SECRET_KEY", "dev"))
    if config_object:
        app.config.from_object(config_object)
   # Criar diretórios necessários
    os.makedirs('static/screenshots', exist_ok=True)
    os.makedirs('static/ocr', exist_ok=True)
    os.makedirs('temp', exist_ok=True)
    # blueprints no novo caminho
    from app.blueprints.routes_auth import bp_auth
    from app.blueprints.routes_dispositivos import bp_dispositivos
    from app.blueprints.routes_emuladores import bp_emuladores
    from app.blueprints.routes_vision import bp_vision
    from app.blueprints.routes_bots import bp_bots
    from app.routes.ocr_routes import ocr_bp

    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_dispositivos)
    app.register_blueprint(bp_emuladores)
    app.register_blueprint(bp_vision)
    app.register_blueprint(bp_bots)
      
    app.register_blueprint(ocr_bp)

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    @app.route("/")
    def home():
        return redirect(url_for("emuladores.gerenciar_emuladores"))

  

    return app
