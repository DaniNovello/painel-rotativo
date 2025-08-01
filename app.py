# app.py (Versão Final e Robusta)
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
from threading import Lock

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
    """
    Inicializa o navegador e faz o login uma única vez.
    Se falhar, a aplicação não deve continuar.
    """
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
        
        # ATENÇÃO: Confirme os seletores corretos para a página de login.
        # Use o "Inspecionar Elemento" do seu navegador.
        user_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
        user_field.send_keys(DKRO_USER)
        
        pass_field = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        pass_field.send_keys(DKRO_PASS)
        
        # Tente usar um seletor mais específico se o 'type=submit' falhar
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()
        
        # Pequena espera para garantir o processamento do login
        time.sleep(5) 
        print("SUCESSO: Navegador inicializado e login efetuado.")
        
        # Atribui à variável global somente se tudo deu certo
        with browser_lock:
            browser = temp_browser
            
    except Exception as e:
        print(f"ERRO CRÍTICO NA INICIALIZAÇÃO: Não foi possível fazer login. A aplicação não funcionará. Erro: {e}")
        temp_browser.quit()

# --- Rotas ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config')
def api_config():
    response = supabase.table('dashboards').select("url", "duration").execute()
    return jsonify({'dashboards': response.data})

@app.route('/screenshot')
def get_screenshot():
    url_to_capture = request.args.get('url')
    if not url_to_capture:
        return "URL não fornecida", 400

    with browser_lock:
        if browser is None:
            print("Erro: O navegador não está inicializado. O login pode ter falhado.")
            return "Erro interno: Navegador indisponível", 500

        try:
            print(f"Navegando para capturar: {url_to_capture}")
            browser.get(url_to_capture)
            # Aumente este tempo se as páginas demorarem para carregar
            time.sleep(7) 
            
            png_data = browser.get_screenshot_as_png()
            print(f"Screenshot de '{url_to_capture}' capturado com sucesso.")
            return send_file(io.BytesIO(png_data), mimetype='image/png')
            
        except Exception as e:
            print(f"ERRO DURANTE CAPTURA: Falha ao tirar screenshot de {url_to_capture}. Reiniciando navegador. Erro: {e}")
            # Se der erro aqui, força a recriação do navegador na próxima vez
            global browser
            browser.quit()
            browser = None
            return "Erro ao gerar screenshot, tente novamente.", 500

# Adicione suas rotas /admin aqui (código idêntico)
# ...

# Inicializa o navegador em uma thread separada para não bloquear o boot da aplicação
from threading import Thread
init_thread = Thread(target=initialize_browser)
init_thread.daemon = True
init_thread.start()

# O if __name__ == '__main__' é usado para testes locais, não para o Gunicorn