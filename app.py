from flask import Flask
from interface.routes_auth import bp_auth
from interface.routes_emuladores import bp_emuladores
from interface.routes_dispositivos import bp_dispositivos

app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Registrar Blueprints
app.register_blueprint(bp_auth)
app.register_blueprint(bp_emuladores)
app.register_blueprint(bp_dispositivos)

@app.route('/')
def home():
    return "<script>window.location.href='/login'</script>"

if __name__ == '__main__':
    # 🚫 NÃO use debug=True nem use_reloader=True aqui
    app.run(debug=False, use_reloader=False)
