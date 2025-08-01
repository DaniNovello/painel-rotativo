import os
import time
import io
from flask import Flask, render_template, jsonify, send_file, request, redirect, url_for
from supabase import create_client, Client
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
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

# --- Gerenciamento do Navegador Selenium ---
browser = None
lock = Lock()

def get_browser():
    """Inicializa e retorna uma instância única do navegador Selenium."""
    global browser
    with lock:
        if browser is None:
            print("Inicializando navegador Selenium...")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            # --- CORREÇÃO ADICIONADA AQUI ---
            # Garante um diretório de dados temporário e isolado para evitar conflitos
            chrome_options.add_argument("--user-data-dir=/tmp/selenium")
            
            browser = webdriver.Chrome(options=chrome_options)
            
            # --- Faz o login no DKRO uma única vez ---
            try:
                print("Tentando fazer login no sistema DKRO...")
                browser.get("https://sistema.dkro.com.br/Login")
                time.sleep(3) 
                
                # ATENÇÃO: Verifique se os IDs "username" e "password" estão corretos
                # na página de login do sistema DKRO.
                browser.find_element(By.ID, "username").send_keys(DKRO_USER) #
                browser.find_element(By.ID, "password").send_keys(DKRO_PASS) #
                browser.find_element(By.XPATH, "//button[@type='submit']").click()
                print("Login no DKRO efetuado com sucesso.")
                time.sleep(5)
            except Exception as e:
                print(f"ERRO CRÍTICO: Falha ao fazer login no DKRO. {e}")
                # Limpa a instância do navegador em caso de falha no login
                browser.quit()
                browser = None
                # Você pode querer levantar uma exceção aqui para parar a aplicação
                # se o login for essencial e não puder ser recuperado.
    return browser

# --- Rotas ---
@app.route('/')
def index():
    """Página principal que exibe as imagens."""
    return render_template('index.html')

@app.route('/api/config')
def api_config():
    """Busca a lista de URLs do Supabase."""
    response = supabase.table('dashboards').select("url", "duration").execute()
    return jsonify({'dashboards': response.data})

@app.route('/screenshot')
def get_screenshot():
    """Tira um screenshot de uma URL específica e retorna a imagem."""
    url_to_capture = request.args.get('url')
    if not url_to_capture:
        return "URL não fornecida", 400

    b = None # Inicializa a variável do navegador
    try:
        b = get_browser()
        if b is None: # Se get_browser falhou em criar uma instância
            raise Exception("Navegador não pôde ser inicializado.")

        print(f"Navegando para: {url_to_capture}")
        b.get(url_to_capture)
        time.sleep(5) 
        
        png_data = b.get_screenshot_as_png()
        print("Screenshot capturado.")
        return send_file(io.BytesIO(png_data), mimetype='image/png')
    except Exception as e:
        print(f"Erro ao capturar screenshot de {url_to_capture}: {e}")
        # --- CORREÇÃO ADICIONADA AQUI ---
        # Garante que o navegador seja encerrado antes de ser reiniciado
        global browser
        if b is not None:
            b.quit() # Encerra o processo do navegador
        browser = None
        return "Erro ao gerar screenshot", 500

# --- Rotas de Administração ---
@app.route('/admin')
def admin():
    """Exibe a página de administração com a lista de dashboards."""
    try:
        # Equivalente a: SELECT id, url, duration FROM dashboards ORDER BY id
        response = supabase.table('dashboards').select("*").order('id').execute()
        return render_template('admin.html', dashboards=response.data)
    except Exception as e:
        print(f"Erro ao buscar do Supabase: {e}")
        return render_template('admin.html', dashboards=[], error="Falha ao carregar dashboards.")

@app.route('/admin/add', methods=['POST'])
def add_dashboard():
    """Adiciona um novo dashboard ao Supabase."""
    url = request.form.get('url')
    duration = request.form.get('duration')
    if url and duration:
        try:
            # Equivalente a: INSERT INTO dashboards (url, duration) VALUES (...)
            supabase.table('dashboards').insert({
                'url': url,
                'duration': int(duration)
            }).execute()
        except Exception as e:
            print(f"Erro ao inserir no Supabase: {e}")
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:dashboard_id>', methods=['POST'])
def delete_dashboard(dashboard_id):
    """Exclui um dashboard do Supabase."""
    try:
        # Equivalente a: DELETE FROM dashboards WHERE id = ...
        supabase.table('dashboards').delete().eq('id', dashboard_id).execute()
    except Exception as e:
        print(f"Erro ao deletar no Supabase: {e}")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)