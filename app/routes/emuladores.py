from flask import Blueprint, render_template, jsonify
from core.gateways import emulator_ctl

bp = Blueprint('emuladores', __name__, url_prefix='/emuladores')


@bp.route('/')
def gerenciar_emuladores():
    """Página principal de gerenciamento"""
    return render_template('emuladores.html')


@bp.route('/listar')
def listar_emuladores():
    """Lista emuladores ativos"""
    try:
        emuladores = emulator_ctl.listar_emuladores_ativos()
        
        return jsonify({
            'sucesso': True,
            'total': len(emuladores),
            'emuladores': emuladores
        })
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'emuladores': []
        }), 500