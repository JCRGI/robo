from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import os
import json
from core.storage import carregar_dispositivos, salvar_dispositivos
from core.adb_manager import AdbManager
from core.image_processor import process_image


bp_dispositivos = Blueprint('dispositivos', __name__)
adb = AdbManager()
conectado = False
device_selecionado = None

@bp_dispositivos.route('/index')
def index():
    if not session.get('logado'):
        return redirect(url_for('auth.login'))
    dispositivos = carregar_dispositivos()
    return render_template('index.html', conectado=conectado, dispositivos=dispositivos, selecionado=device_selecionado)


@bp_dispositivos.route('/adicionar_dispositivo', methods=['POST'])
def adicionar_dispositivo():
    nome = request.form.get('nome')
    ip = request.form.get('ip')

    if not nome or not ip:
        flash("Preencha todos os campos!", "warning")
        return redirect(url_for('dispositivos.index'))

    dispositivos = carregar_dispositivos()
    dispositivos.append({"nome": nome, "ip": ip})
    salvar_dispositivos(dispositivos)

    flash(f"Dispositivo '{nome}' adicionado com sucesso!", "success")
    return redirect(url_for('dispositivos.index'))


@bp_dispositivos.route('/conectar_dispositivo/<ip>', methods=['POST'])
def conectar_dispositivo(ip):
    global conectado, device_selecionado
    try:
        os.system(f"adb connect {ip}")
        adb.connect_device()
        conectado = True
        device_selecionado = ip
        flash(f"Conectado ao dispositivo {ip}", "success")
    except Exception as e:
        flash(f"Erro ao conectar: {e}", "danger")
    return redirect(url_for('dispositivos.index'))


@bp_dispositivos.route('/executar', methods=['POST'])
def executar():
    if not conectado:
        flash("Conecte um dispositivo primeiro!", "warning")
        return redirect(url_for('dispositivos.index'))

    comando = request.form.get('comando')
    try:
        resultado = adb.run_shell(comando)
        flash(f"Resultado:\n{resultado}", "info")
    except Exception as e:
        flash(f"Erro ao executar comando: {e}", "danger")
    return redirect(url_for('dispositivos.index'))


@bp_dispositivos.route('/screenshot', methods=['POST'])
def screenshot():
    if not conectado:
        flash("Conecte um dispositivo primeiro!", "warning")
        return redirect(url_for('dispositivos.index'))

    nome_arquivo = request.form.get('nome_arquivo') or "screenshot.png"
    try:
        adb.capture_screen(nome_arquivo)
        flash(f"Screenshot salva como {nome_arquivo}", "success")
    except Exception as e:
        flash(f"Erro ao tirar screenshot: {e}", "danger")
    return redirect(url_for('dispositivos.index'))


@bp_dispositivos.route('/ocr', methods=['POST'])
def ocr_dispositivo():
    if not conectado:
        flash("Conecte um dispositivo primeiro!", "warning")
        return redirect(url_for('dispositivos.index'))

    nome_arquivo = "screenshot.png"
    try:
        adb.capture_screen(nome_arquivo)
        texto = process_image(nome_arquivo)
        flash(f"OCR concluído:\n{texto}", "info")
    except Exception as e:
        flash(f"Erro ao processar OCR: {e}", "danger")

    return redirect(url_for('dispositivos.index'))