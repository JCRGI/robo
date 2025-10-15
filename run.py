"""Script para iniciar aplicação Flask"""

from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Iniciando Flask App")
    print("="*70)
    print(f"URL: http://127.0.0.1:5000")
    print(f"Blueprints registrados:")
    for blueprint in app.blueprints.values():
        print(f"  - {blueprint.name}: {blueprint.url_prefix or '/'}")
    print("="*70 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=True
    )
