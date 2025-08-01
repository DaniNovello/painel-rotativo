# app.py (Versão com Seletores Corretos)
import os
import time
import io
from flask import Flask, render_template, jsonify, send_file, request, redirect, url_for
from supabase import create_client, Client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Lock, Thread
import traceback

# --- Configuração ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DKRO_USER = os.environ.get("DKRO_USER")
DKRO_PASS = os.environ.get("DKRO_PASS")

if not all([SUPABASE_URL, SUPABASE_KEY, DKRO_USER, DKRO_PASS]):
    raise ValueError("Verifique as variáveis de ambiente: SUPABASE_URL, SUPABASE_KEY, DKRO_USER, DKRO_PASS")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

# --- Gerenciamento Centralizado do Navegador ---
browser = None
browser_lock = Lock()

def initialize_browser():
    """Inicializa o navegador e faz o login uma única vez."""
    global browser
    print("Tentando inicializar o navegador e fazer login...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-data-dir=/tmp/selenium")
    
    temp_browser = webdriver.Chrome(options=chrome_options)
    
    try:
        temp_browser.get("https://sistema.dkro.com.br/Login")
        wait = WebDriverWait(temp_browser, 20)
        
        # --- SELETORES CORRIGIDOS COM BASE NAS SUAS IMAGENS ---
        # Campo de usuário com id="username"
        wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(DKRO_USER)
        
        # Campo de senha com id="password"
        wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(DKRO_PASS)
        
        # Botão de login (que é um div) pela sua classe
        login_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "dtn-submit")))
        login_button.click()
        
        time.sleep(8) 
        
        if "Login" in temp_browser.current_url:
            raise Exception("Login falhou, ainda estamos na página de Login. Verifique usuário e senha.")
        
        print("SUCESSO: Navegador inicializado e login efetuado.")
        
        with browser_lock:
            browser = temp_browser
            
    except Exception as e:
        print("--- ERRO CRÍTICO NA INICIALIZAÇÃO ---")
        print(f"Não foi possível fazer login. A aplicação não funcionará.")
        traceback.print_exc()
        temp_browser.quit()

# --- Rotas (O resto do código permanece o mesmo) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config')
def api_config():
    response = supabase.table('dashboards').select("url", "duration").execute()
    return jsonify({'dashboards': response.data})

@app.route('/screenshot')
def get_screenshot():
    global browser
    
    url_to_capture = request.args.get('url')
    if not url_to_capture:
        return "URL não fornecida", 400

    with browser_lock:
        if browser is None:
            print("Erro: O navegador não está inicializado. O login pode ter falhado.")
            return "Erro interno: Navegador indisponível", 500

        try:
            browser.get(url_to_capture)
            time.sleep(7)
            png_data = browser.get_screenshot_as_png()
            return send_file(io.BytesIO(png_data), mimetype='image/png')
            
        except Exception as e:
            print(f"ERRO DURANTE CAPTURA: {e}")
            if browser:
                browser.quit()
            browser = None
            return "Erro ao gerar screenshot", 500

# Suas rotas /admin
@app.route('/admin')
def admin():
    response = supabase.table('dashboards').select("*").order('id').execute()
    return render_template('admin.html', dashboards=response.data)

@app.route('/admin/add', methods=['POST'])
def add_dashboard():
    url = request.form.get('url')
    duration = request.form.get('duration')
    supabase.table('dashboards').insert({'url': url, 'duration': int(duration)}).execute()
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:dashboard_id>', methods=['POST'])
def delete_dashboard(dashboard_id):
    supabase.table('dashboards').delete().eq('id', dashboard_id).execute()
    return redirect(url_for('admin'))

# Inicializa o navegador em segundo plano
init_thread = Thread(target=initialize_browser)
init_thread.daemon = True
init_thread.start()