from flask import Blueprint, render_template, request, jsonify, send_from_directory, Response, stream_with_context
import os
import json
import asyncio

from modules.gerar_imagens import run_gerar_imagens, calcular_indices, gerar_eventos_para_stream, gerar_imagens_async
from modules.paths import get_paths

imagens_bp = Blueprint("imagens", __name__)


@imagens_bp.route("/imagens", methods=["GET"])
def imagens_page():
    path = get_paths()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    os.makedirs(path["imagens"], exist_ok=True)
    arquivos = os.listdir(path["imagens"])
    arquivos_dict = {}
    for nome in arquivos:
        if nome.startswith("imagem") and (nome.endswith(".jpg") or nome.endswith(".png") or nome.endswith(".mp4")):
            idx = nome.replace("imagem", "").split(".")[0]
            if idx.isdigit():
                arquivos_dict[int(idx)] = nome

    return render_template(
        "generate_imagem.html",
        page_title="Gerar Imagens",
        cenas=cenas,
        arquivos_midia=arquivos_dict,
    )


@imagens_bp.route("/imagens", methods=["POST"])
def imagens_run():
    scope = request.form.get("scope", "all")
    single = request.form.get("single_index", type=int)
    start = request.form.get("from_index", type=int)
    selected = request.form.get("selected_indices")

    path = get_paths()
    with open(path["cenas"], encoding="utf-8") as f:
        total = len(json.load(f))

    try:
        indices = calcular_indices(scope, single, start, total, selected)
        resultado = run_gerar_imagens(indices)
    except Exception as e:
        print(f"❌ Erro em /imagens: {str(e)}")
        return jsonify({"error": str(e)}), 400

    return jsonify({"status": "ok", "cenas": resultado["cenas"], "logs": resultado["logs"]})


@imagens_bp.route("/modules/imagens/<path:filename>")
def serve_module_images(filename):
    path = get_paths()
    return send_from_directory(path["imagens"], filename)


@imagens_bp.route("/imagens_stream", methods=["GET"])
def imagens_stream():
    scope = request.args.get("scope", "all")
    single = request.args.get("single_index", type=int)
    start = request.args.get("from_index", type=int)
    selected = request.args.get("selected_indices")

    return Response(
        stream_with_context(gerar_eventos_para_stream(scope, single, start, selected)),
        mimetype="text/event-stream",
    )


@imagens_bp.route("/editar_prompt", methods=["POST"])
def editar_prompt():
    data = request.get_json()
    index = int(data["index"])
    novo = data["novo_prompt"]

    path = get_paths()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["prompt_imagem"] = novo

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})


@imagens_bp.route("/substituir_imagem", methods=["POST"])
def substituir_imagem():
    data = request.get_json()
    index = int(data["index"])
    novo = data["novo_prompt"]

    path = get_paths()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["prompt_imagem"] = novo

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    logs = []
    asyncio.run(gerar_imagens_async(cenas, [index], logs))

    with open(path["cenas_com_imagens"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})


@imagens_bp.route("/upload_imagem", methods=["POST"])
def upload_imagem():
    try:
        index = int(request.form["index"])
        imagem = request.files.get("imagem")
        if not imagem:
            return jsonify({"status": "erro", "msg": "Nenhum arquivo enviado"}), 400

        ext = os.path.splitext(imagem.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".mp4"]:
            return jsonify({"status": "erro", "msg": "Formato não suportado"}), 400

        path = get_paths()
        os.makedirs(path["imagens"], exist_ok=True)

        nome_base = f"imagem{index+1}"
        for old_ext in [".jpg", ".png", ".mp4"]:
            caminho_antigo = os.path.join(path["imagens"], nome_base + old_ext)
            if os.path.exists(caminho_antigo):
                os.remove(caminho_antigo)

        caminho = os.path.join(path["imagens"], nome_base + ext)
        imagem.save(caminho)

        with open(path["cenas"], encoding="utf-8") as f:
            cenas = json.load(f)

        cenas[index]["arquivo_local"] = caminho
        cenas[index]["image_url"] = f"/modules/imagens/{nome_base}{ext}"

        with open(path["cenas_com_imagens"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"❌ Erro em upload_imagem: {e}")
        return jsonify({"status": "erro", "msg": str(e)}), 500
