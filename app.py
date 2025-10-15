import os

from flask import Flask, render_template

from app import create_app
from app.routes.ocr_routes import ocr_bp

app = Flask(__name__)

# Registrar blueprint
app.register_blueprint(ocr_bp)

app = create_app(os.getenv("FLASK_CONFIG", "configs.config.DevConfig"))


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
