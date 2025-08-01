# app.py
import json
from flask import Flask, render_template, jsonify, abort # type: ignore

app = Flask(__name__)

def get_config():
    """Lê o arquivo de configuração e retorna os dados."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Se o arquivo não existir, aborta com um erro 404.
        print("Erro: O arquivo 'config.json' não foi encontrado.")
        abort(404, description="Arquivo de configuração não encontrado.")
    except json.JSONDecodeError:
        # Se o JSON for inválido, aborta com um erro 500.
        print("Erro: O arquivo 'config.json' contém um JSON inválido.")
        abort(500, description="Erro ao ler o arquivo de configuração.")

@app.route('/')
def index():
    """Renderiza a página principal do painel."""
    return render_template('index.html')

@app.route('/api/config')
def api_config():
    """Endpoint da API para fornecer a configuração dos dashboards."""
    config_data = get_config()
    return jsonify(config_data)

if __name__ == '__main__':
    # Roda o servidor em modo de desenvolvimento.
    # O host 0.0.0.0 permite acesso de outros dispositivos na mesma rede.
    app.run(debug=True, host='0.0.0.0', port=5000)