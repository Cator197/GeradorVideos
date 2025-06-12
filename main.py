import os
import asyncio
from flask import Flask, render_template_string, request, redirect, url_for

# # Importa seus módulos existentes
# from gerar_imagens import main as gerar_imagens_main
# from gerar_narracoes import main as gerar_narracoes_main
# from gerar_legendas import main as gerar_legendas_main
# from juntar_cenas import main as montar_videos_main

app = Flask(__name__)

# --- Base Template com sidebar e header responsivo ---
BASE_TEMPLATE = '''
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ page_title }}</title>
  <style>
    body { margin:0; padding:0; font-family:Arial,sans-serif; }
    .container { display:flex; min-height:100vh; }
    aside.sidebar { width:200px; background:#222; color:#fff; }
    aside.sidebar nav ul { list-style:none; margin:0; padding:0; }
    aside.sidebar nav li { border-bottom:1px solid #444; }
    aside.sidebar nav a { display:block; padding:0.75rem 1rem; color:#fff; text-decoration:none; }
    aside.sidebar nav a:hover { background:#444; }
    .main { flex:1; background:#f5f5f5; }
    header { background:#fff; padding:1rem; border-bottom:1px solid #ddd; }
    header h1 { margin:0; font-size:1.5rem; }
    section.content { padding:1.5rem; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:1rem; }
    .card { background:#fff; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1); text-align:center; padding:1.5rem; }
    .card button { background:#007bff; border:none; color:#fff; padding:0.75rem; width:100%; border-radius:4px; cursor:pointer; }
    .card button:hover { background:#0056b3; }
    .complete-container { background:#fff; border-radius:8px; padding:2rem; }
    .row { display:flex; flex-wrap:wrap; gap:1rem; }
    .col { flex:1; min-width:200px; }
    textarea { width:100%; height:150px; padding:0.5rem; font-size:1rem; }
    .config-panel { background:#fafafa; padding:1rem; border:1px solid #ddd; border-radius:4px; }
    .config-panel label { display:block; margin-bottom:0.5rem; }
    .progress-bar { background:#eee; border-radius:4px; overflow:hidden; height:20px; margin:1rem 0; }
    .progress-fill { background:#007bff; height:100%; width:0%; }
    .progress-log { background:#000; color:#0f0; padding:1rem; height:200px; overflow:auto; font-family:monospace; }
  </style>
</head>
<body>
  <div class="container">
    <aside class="sidebar">
      <nav>
        <ul>
          <li><a href="{{ url_for('index') }}">Início</a></li>
          <li><a href="{{ url_for('complete_page') }}">Gerar Vídeo Completo</a></li>
          <li><a href="{{ url_for('run_step', step='imagens') }}">Gerar Imagem</a></li>
          <li><a href="{{ url_for('run_step', step='narracoes') }}">Gerar Narração</a></li>
          <li><a href="{{ url_for('run_step', step='legendas') }}">Gerar Legendas</a></li>
          <li><a href="{{ url_for('run_step', step='montar') }}">Montar Cenas</a></li>
          <li><a href="{{ url_for('run_step', step='unir') }}">Unir Vídeos</a></li>
          <li><a href="{{ url_for('config_page') }}">Configurações</a></li>
        </ul>
      </nav>
    </aside>

    <div class="main">
      <header><h1>{{ page_title }}</h1></header>
      <section class="content">
        {{ content|safe }}
      </section>
    </div>
  </div>
</body>
</html>
'''

# --- Conteúdo das páginas específicas ---
INDEX_CONTENT = '''
<div class="grid">
  <div class="card"><button onclick="location.href='{{ url_for('complete_page') }}'">Gerar Vídeo Completo</button></div>
  <div class="card"><button onclick="location.href='{{ url_for('run_step', step='imagens') }}'">Gerar Imagem</button></div>
  <div class="card"><button onclick="location.href='{{ url_for('run_step', step='narracoes') }}'">Gerar Narração</button></div>
  <div class="card"><button onclick="location.href='{{ url_for('run_step', step='legendas') }}'">Gerar Legendas</button></div>
  <div class="card"><button onclick="location.href='{{ url_for('run_step', step='montar') }}'">Montar Cenas</button></div>
  <div class="card"><button onclick="location.href='{{ url_for('run_step', step='unir') }}'">Unir Vídeos</button></div>
  <div class="card"><button onclick="location.href='{{ url_for('config_page') }}'">Configurações</button></div>
</div>
'''

COMPLETE_CONTENT = '''
<div class="complete-container">
  <div class="row">
    <div class="col">
      <label><strong>Prompt inicial:</strong></label>
      <textarea id="initial_prompt" placeholder="Digite seu prompt..."></textarea>
    </div>
    <div class="col config-panel">
      <fieldset><legend>Configurações</legend>
        <label><input type="checkbox"> gerar imagens <button>upar</button></label>
        <label><input type="checkbox"> narração <select><option>Eleven Labs</option><option>API</option></select></label>
        <label><input type="checkbox"> legenda palavras/scene <input type="number" style="width:60px"></label>
        <button id="generate_video">Gerar Vídeo</button>
      </fieldset>
    </div>
  </div>
  <div class="progress-bar"><div class="progress-fill"></div></div>
  <div class="progress-log"><pre id="log"></pre></div>
</div>
'''

# --- Rotas ---
@app.route('/')
def index():
    return render_template_string(
        BASE_TEMPLATE,
        page_title="Início",
        content=INDEX_CONTENT
    )

@app.route('/complete')
def complete_page():
    return render_template_string(
        BASE_TEMPLATE,
        page_title="Gerar Vídeo Completo",
        content=COMPLETE_CONTENT
    )

@app.route('/run')
def run_step():
    step = request.args.get('step')
    if step == 'imagens':
        asyncio.run(gerar_imagens_main())
    elif step == 'narracoes':
        gerar_narracoes_main()
    elif step == 'legendas':
        gerar_legendas_main()
    elif step in ('montar', 'unir'):
        montar_videos_main()
    return redirect(url_for('index'))

@app.route('/config')
def config_page():
    # Template de configurações pode ser adicionado aqui
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
