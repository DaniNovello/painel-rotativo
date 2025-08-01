# app.py
import os
from flask import Flask, render_template, jsonify, request, redirect, url_for # type: ignore
from supabase import create_client, Client # type: ignore

# --- Configuração ---
# É uma boa prática carregar isso de variáveis de ambiente
# Para teste local, você pode colar suas chaves aqui.
# Para o deploy (Render.com), use as "Environment Variables" do painel.
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Validação para garantir que as chaves foram configuradas
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("As variáveis de ambiente SUPABASE_URL e SUPABASE_KEY são necessárias.")

# Inicializa o cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# --- Rotas do Painel ---
@app.route('/')
def index():
    """Renderiza a página principal do painel."""
    return render_template('index.html')

@app.route('/api/config')
def api_config():
    """Endpoint da API que busca os dashboards do Supabase."""
    try:
        # Equivalente a: SELECT url, duration FROM dashboards
        response = supabase.table('dashboards').select("url", "duration").execute()
        # A API retorna os dados dentro de uma chave "data"
        return jsonify({'dashboards': response.data})
    except Exception as e:
        print(f"Erro ao buscar do Supabase: {e}")
        return jsonify({'error': 'Falha ao buscar configuração'}), 500

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

# --- Inicialização ---
if __name__ == '__main__':
    # Roda o servidor. Não precisamos mais do db.create_all()!
    app.run(debug=True, host='0.0.0.0', port=5000)