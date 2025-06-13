import os
import json
import asyncio
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask import send_from_directory

# Importe sua função refatorada de geração de imagens
from modules.gerar_imagens import run_gerar_imagens
from modules.gerar_narracao import run_gerar_narracoes
from modules.gerar_SRT import run_gerar_legendas

# Importe de maneira similar suas outras etapas, por exemplo:
# from modules.gerar_narracoes import run_gerar_narracoes
# from modules.gerar_legendas import run_gerar_legendas
# from modules.juntar_cenas import run_montar_videos

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", page_title="Início")

@app.route("/complete")
def complete():
    return render_template("complete.html", page_title="Gerar Vídeo Completo")

@app.route("/generate_narracao")
def generate_narracao():
    path = os.path.join(app.root_path, "modules", "cenas.json")
    if not os.path.exists(path):
        return "Arquivo cenas.json não encontrado", 500
    with open(path, "r", encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_narracao.html", cenas=cenas)


@app.route("/imagens", methods=["GET"])
def imagens_page():
    # Carrega cenas para popular a listbox
    path = os.path.join(app.root_path, "modules", "cenas.json")
    with open(path, encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_imagem.html",
                           page_title="Gerar Imagens",
                           cenas=cenas)

@app.route("/imagens", methods=["POST"])
def imagens_run():
    scope  = request.form.get("scope", "all")
    single = request.form.get("single_index", type=int)
    start  = request.form.get("from_index",   type=int)

    # carrega total
    path = os.path.join(app.root_path, "modules", "cenas.json")
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    # monta índices
    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    # executa e captura logs
    try:
        resultado = run_gerar_imagens(indices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "cenas":   resultado["cenas"],
        "logs":    resultado["logs"]
    })

@app.route('/modules/imagens/<path:filename>')
def serve_module_images(filename):
    return send_from_directory(
        os.path.join(app.root_path, 'modules', 'imagens'),
        filename
    )

@app.route("/narracoes", methods=["POST"])
def narracoes_run():
    scope  = request.form.get("scope", "all")
    single = request.form.get("single_index", type=int)
    start  = request.form.get("from_index",   type=int)

    path = os.path.join(app.root_path, "modules", "cenas_com_imagens.json")
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    try:
        resultado = run_gerar_narracoes(indices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "logs": resultado["logs"],
        "cenas": resultado["cenas"]
    })

@app.route("/generate_legenda")
def generate_legenda():
    path = os.path.join(app.root_path, "modules", "cenas_com_imagens.json")
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500
    with open(path, "r", encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_legenda.html", cenas=cenas)

@app.route("/legendas", methods=["POST"])
def gerar_legendas():

    scope  = request.form.get("scope", "all")
    single = request.form.get("single_index", type=int)
    start  = request.form.get("from_index",   type=int)

    path = os.path.join(app.root_path, "modules", "cenas_com_imagens.json")
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    try:
        resultado = run_gerar_legendas(indices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "logs": resultado["logs"],
        "cenas": resultado["cenas"]
    })

@app.route("/generate_montagem")
def generate_montagem():
    path = os.path.join(app.root_path, "modules", "cenas_com_imagens.json")
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500
    with open(path, "r", encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_montagem.html", cenas=cenas)

@app.route("/montagem", methods=["POST"])
def montagem_cenas():
    from modules.montar_cenas import run_montar_cenas

    scope   = request.form.get("scope", "all")
    single  = request.form.get("single_index", type=int)
    start   = request.form.get("from_index",   type=int)
    tipo    = request.form.get("tipo", "hard")
    cor     = request.form.get("cor", "white")
    tamanho = request.form.get("tamanho", type=int)
    posicao = request.form.get("posicao", "bottom")

    usar_soft = tipo == "soft"

    path = os.path.join(app.root_path, "modules", "cenas_com_imagens.json")
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    try:
        resultado = run_montar_cenas(indices, usar_soft, cor, tamanho, posicao)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "logs": resultado["logs"]
    })

@app.route("/generate_final")
def generate_final():
    path = os.path.join(app.root_path, "modules", "cenas_com_imagens.json")
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500
    with open(path, "r", encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_final.html", cenas=cenas)

@app.route("/finalizar", methods=["POST"])
def finalizar_video():
    try:
        from modules.juntar_cenas import run_juntar_cenas, exportar_para_capcut
        tipo = request.form.get("acao", "video")
        transicao = request.form.get("transicao", "cut")

        usar_trilha = request.form.get("usar_trilha") == "true"
        usar_marca  = request.form.get("usar_marca") == "true"

        trilha_path = None
        marca_path  = None

        # Salvar arquivos enviados, se houver
        if usar_trilha and "trilha" in request.files:
            trilha_file = request.files["trilha"]
            trilha_path = os.path.join("modules", "videos_final", trilha_file.filename)
            trilha_file.save(trilha_path)

        if usar_marca and "marca" in request.files:
            marca_file = request.files["marca"]
            marca_path = os.path.join("modules", "videos_final", marca_file.filename)
            marca_file.save(marca_path)

        if tipo == "video":
            resultado = run_juntar_cenas(
                tipo_transicao=transicao,
                usar_musica=usar_trilha,
                trilha_path=trilha_path,
                volume=0.2,
                usar_watermark=usar_marca,
                marca_path=marca_path,
                opacidade=0.3,
                posicao="('right','bottom')"
            )
            return jsonify(resultado)
        else:
            export = exportar_para_capcut(
                trilha_path=trilha_path if usar_trilha else None,
                marca_path=marca_path if usar_marca else None
            )
            return jsonify(export)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/modules/videos_cenas/<path:filename>')
def serve_videos_cenas(filename):
    return send_from_directory(
        os.path.join(app.root_path, 'modules', 'videos_cenas'),
        filename
    )


@app.route("/config")
def config_page():
    # Se criar um config.html, troque abaixo
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=8080)
