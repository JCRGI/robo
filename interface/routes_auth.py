from flask import Blueprint, render_template, request, redirect, url_for, flash, session

bp_auth = Blueprint('auth', __name__)

@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == "1234":  # 🔐 Altere aqui sua senha real
            session['logado'] = True
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for('emuladores.gerenciar_emuladores'))
        else:
            flash("Senha incorreta!", "danger")

    return render_template('login.html')


@bp_auth.route('/logout')
def logout():
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for('auth.login'))
