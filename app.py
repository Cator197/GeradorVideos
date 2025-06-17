import os
import json
import asyncio
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask import send_from_directory, stream_with_context
import pydub
from pydub import AudioSegment, silence
from modules.config import salvar_config, carregar_config
from flask import current_app
import tkinter as tk
from tkinter import filedialog
from flask import send_from_directory
from modules.config import get_config
import os
from flask import send_file

# Importe sua função refatorada de geração de imagens
from modules.gerar_imagens import run_gerar_imagens
from modules.gerar_narracao import run_gerar_narracoes
from modules.gerar_SRT import run_gerar_legendas

# Importe de maneira similar suas outras etapas, por exemplo:
# from modules.gerar_narracoes import run_gerar_narracoes
# from modules.gerar_legendas import run_gerar_legendas
# from modules.juntar_cenas import run_montar_videos

app = Flask(__name__)
app.config['USUARIO_CONFIG'] = carregar_config()
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

@app.route("/modules/imagens/<path:filename>")
def serve_module_images(filename):
    pasta_salvar = get_config("pasta_salvar")
    pasta_imagens = os.path.join(pasta_salvar, "imagens")
    return send_from_directory(pasta_imagens, filename)

@app.route("/modules/audio/<path:filename>")
def serve_module_audio(filename):
    pasta = os.path.join(get_config("pasta_salvar") or ".", "audios_narracoes")
    return send_from_directory(pasta, filename)

@app.route("/narracoes", methods=["POST"])
def narracoes_run():
    scope  = request.form.get("scope", "all")
    single = request.form.get("single_index", type=int)
    start  = request.form.get("from_index",   type=int)

    path = caminho_cenas_final()
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

@app.route('/preview_video/<int:idx>')
def preview_video(idx):
    base_path = get_config("pasta_salvar") or "default"
    video_path = os.path.join(base_path, "videos_cenas", f"video{idx}.mp4")

    if not os.path.isfile(video_path):
        return "Vídeo não encontrado", 404

    return send_file(video_path, mimetype='video/mp4')

@app.route("/generate_legenda")
def generate_legenda():
    path = caminho_cenas_final()
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

    path = caminho_cenas_final()
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
        resultado = run_gerar_legendas(indices, tipo=tipo)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "logs": resultado["logs"],
        "cenas": resultado["cenas"]
    })

@app.route("/generate_montagem")
def generate_montagem():
    path = caminho_cenas_final()
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500
    with open(path, "r", encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_montagem.html", cenas=cenas)

def caminho_cenas_final():
    from modules.config import get_config
    return os.path.join(get_config("pasta_salvar") or ".", "cenas_com_imagens.json")

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

    path = caminho_cenas_final()
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
    path = caminho_cenas_final()
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

from flask import Response, stream_with_context
import time

@app.route("/legendas_stream", methods=["GET"])
def gerar_legendas_stream():
    scope  = request.args.get("scope", "all")
    single = request.args.get("single_index", type=int)
    start  = request.args.get("from_index", type=int)

    path = caminho_cenas_final()
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return Response("data: ❌ Parâmetros inválidos\n\n", mimetype='text/event-stream')

    def gerar_eventos():
        from modules.gerar_SRT import gerar_srt_por_palavra
        import time

        with open(path, "r", encoding="utf-8") as f:
            cenas = json.load(f)

        for idx in indices:
            pasta_audio=os.path.join(get_config("pasta_salvar") or ".", "audios_narracoes")
            audio_path=os.path.join(pasta_audio, f"narracao{idx + 1}.mp3")
            pasta_legendas=os.path.join(get_config("pasta_salvar") or ".", "legendas_srt")
            os.makedirs(pasta_legendas, exist_ok=True)

            srt_path=os.path.join(pasta_legendas, f"legenda{idx + 1}.srt")

            if os.path.exists(audio_path):
                yield f"data: 📝 Gerando legenda {idx+1}\n\n"
                gerar_srt_por_palavra(audio_path, srt_path)
                yield f"data: ✅ Legenda {idx+1} salva\n\n"
                cenas[idx]["srt_path"] = srt_path
            else:
                yield f"data: ⚠️ Áudio {idx+1} não encontrado\n\n"

            with open(path, "w", encoding="utf-8") as f:
                json.dump(cenas, f, ensure_ascii=False, indent=2)

            time.sleep(0.1)  # opcional, só para espaçar visualmente

        yield f"data: 🔚 Fim do processo\n\n"

    return Response(stream_with_context(gerar_eventos()), mimetype='text/event-stream')

@app.route("/narracao_stream", methods=["GET"])
def gerar_narracoes_stream():
    scope  = request.args.get("scope", "all")
    single = request.args.get("single_index", type=int)
    start  = request.args.get("from_index", type=int)
    fonte  = request.args.get("fonte", "Brian")  # se quiser usar

    path = caminho_cenas_final()
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return Response("data: ❌ Parâmetros inválidos\n\n", mimetype='text/event-stream')

    def gerar_eventos():
        from modules.gerar_narracao import iniciar_driver, login, gerar_e_baixar
        import time

        with open(path, encoding="utf-8") as f:
            cenas = json.load(f)

        yield f"data: 🚀 Iniciando geração de narrações...\n\n"
        driver = iniciar_driver()
        try:
            login(driver)
            for i in indices:
                texto = cenas[i].get("narracao")
                if not texto:
                    yield f"data: ⚠️ Cena {i+1} sem texto.\n\n"
                    continue

                yield f"data: 🎙️ Gerando narração {i+1}\n\n"
                path_audio = gerar_e_baixar(driver, texto, i)
                cenas[i]["audio_path"] = path_audio
                yield f"data: ✅ Narração {i+1} salva\n\n"

                with open(path, "w", encoding="utf-8") as f:
                    json.dump(cenas, f, ensure_ascii=False, indent=2)

                time.sleep(0.2)
        finally:
            driver.quit()

        yield f"data: 🔚 Fim do processo\n\n"

    return Response(stream_with_context(gerar_eventos()), mimetype='text/event-stream')


@app.route("/montagem_stream", methods=["GET"])
def montagem_stream():
    scope   = request.args.get("scope", "all")
    single  = request.args.get("single_index", type=int)
    start   = request.args.get("from_index", type=int)
    tipo    = request.args.get("tipo", "hard")
    cor     = request.args.get("cor", "white")
    tamanho = request.args.get("tamanho", type=int)
    posicao = request.args.get("posicao", "bottom")

    usar_soft = tipo == "soft"

    path = caminho_cenas_final()
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return Response("data: ❌ Parâmetros inválidos\n\n", mimetype='text/event-stream')

    def gerar_eventos():
        from modules.montar_cenas import run_montar_cenas
        import time

        yield f"data: 🚀 Iniciando montagem das cenas...\n\n"
        resultado = run_montar_cenas(indices, usar_soft, cor, tamanho, posicao)
        logs = resultado["logs"]

        for log in logs:
            yield f"data: {log}\n\n"
            time.sleep(0.1)

        yield f"data: 🔚 Fim do processo\n\n"

    return Response(stream_with_context(gerar_eventos()), mimetype='text/event-stream')

@app.route("/finalizar_stream", methods=["GET"])
def finalizar_stream():
    try:
        from modules.juntar_cenas import run_juntar_cenas, exportar_para_capcut

        tipo = request.args.get("acao", "video")
        transicao = request.args.get("transicao", "cut")
        usar_trilha = request.args.get("usar_trilha") == "true"
        usar_marca = request.args.get("usar_marca") == "true"

        trilha_path = None
        marca_path  = None

        def gerar_eventos():
            yield f"data: 🚀 Iniciando montagem final...\n\n"

            if usar_trilha:
                trilha_path_param = request.args.get("trilha_path")
                if trilha_path_param and os.path.exists(trilha_path_param):
                    yield f"data: 🎵 Usando trilha: {trilha_path_param}\n\n"
                    nonlocal trilha_path
                    trilha_path = trilha_path_param

            if usar_marca:
                marca_path_param = request.args.get("marca_path")
                if marca_path_param and os.path.exists(marca_path_param):
                    yield f"data: 🌊 Usando marca: {marca_path_param}\n\n"
                    nonlocal marca_path
                    marca_path = marca_path_param

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
            else:
                resultado = exportar_para_capcut(
                    trilha_path=trilha_path if usar_trilha else None,
                    marca_path=marca_path if usar_marca else None
                )

            for linha in resultado.get("logs", []):
                yield f"data: {linha}\n\n"

            yield f"data: 🔚 Finalização concluída\n\n"

        return Response(stream_with_context(gerar_eventos()), mimetype='text/event-stream')

    except Exception as e:
        return Response(f"data: ❌ Erro: {str(e)}\n\n", mimetype='text/event-stream')

@app.route("/imagens_stream", methods=["GET"])
def imagens_stream():
    scope  = request.args.get("scope", "all")
    single = request.args.get("single_index", type=int)
    start  = request.args.get("from_index", type=int)

    path = os.path.join(app.root_path, "modules", "cenas.json")
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return Response("data: ❌ Parâmetros inválidos\n\n", mimetype='text/event-stream')

    def gerar_eventos():
        from modules.gerar_imagens import _gerar
        import asyncio

        with open(path, encoding="utf-8") as f:
            cenas = json.load(f)

        logs = []

        async def gerar_async():
            await _gerar(cenas, indices, logs)

        asyncio.run(gerar_async())

        for log in logs:
            yield f"data: {log}\n\n"

        # Caminho correto usando a pasta configurada + cenas_com_imagens.json
        saida_json=os.path.join(get_config("pasta_salvar") or ".", "cenas_com_imagens.json")

        with open(saida_json, "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        yield f"data: 🔚 Geração de imagens finalizada\n\n"

    return Response(stream_with_context(gerar_eventos()), mimetype='text/event-stream')

@app.route("/complete_stream", methods=["GET"])
def complete_stream():
    from modules.parser_prompts import parse_prompts_txt
    from modules.gerar_imagens import run_gerar_imagens
    from modules.gerar_narracao import run_gerar_narracoes
    from modules.gerar_SRT import run_gerar_legendas
    from modules.montar_cenas import run_montar_cenas
    from modules.juntar_cenas import run_juntar_cenas

    def gerar_tudo():
        yield f"data: 🧠 Lendo prompts e criando cenas.json...\n\n"
        cenas = parse_prompts_txt("modules/prompts.txt")
        with open("modules/cenas.json", "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=4)
        yield f"data: ✅ Prompts processados: {len(cenas)} cenas\n\n"

        indices = list(range(len(cenas)))

        yield f"data: 🎨 Gerando imagens...\n\n"
        imagens = run_gerar_imagens(indices)
        for log in imagens["logs"]:
            yield f"data: {log}\n\n"

        yield f"data: 🎙️ Gerando narrações...\n\n"
        narracoes = run_gerar_narracoes(indices)
        for log in narracoes["logs"]:
            yield f"data: {log}\n\n"

        yield f"data: ✍️ Gerando legendas...\n\n"
        legendas = run_gerar_legendas(indices)
        for log in legendas["logs"]:
            yield f"data: {log}\n\n"

        yield f"data: 🧩 Montando cenas...\n\n"
        montagem = run_montar_cenas(indices, usar_soft=False, cor="white", tamanho=24, posicao="bottom")
        for log in montagem["logs"]:
            yield f"data: {log}\n\n"

        yield f"data: 🎞️ Juntando vídeo final...\n\n"
        final = run_juntar_cenas(tipo_transicao="cut", usar_musica=False, trilha_path=None, volume=0.2,
                                 usar_watermark=False, marca_path=None, opacidade=0.3, posicao="('right','bottom')")
        for log in final["logs"]:
            yield f"data: {log}\n\n"

        yield f"data: ✅ Pipeline completa finalizada\n\n"

    return Response(stream_with_context(gerar_tudo()), mimetype='text/event-stream')

@app.route("/remover_silencio")
def remover_silencio():
    min_silence = float(request.args.get("min_silence", "0.3"))

    # Usa a pasta salva nas configurações
    base_path = get_config("pasta_salvar") or os.path.join(app.root_path, "modules")
    pasta = os.path.join(base_path, "audios_narracoes")

    if not os.path.exists(pasta):
        return jsonify({"status": "erro", "error": f"Pasta não encontrada: {pasta}"}), 400

    arquivos = [f for f in os.listdir(pasta) if f.endswith(".mp3")]
    count = 0

    for nome in arquivos:
        caminho = os.path.join(pasta, nome)
        try:
            audio = AudioSegment.from_file(caminho, format="mp3")
            chunks = silence.split_on_silence(
                audio,
                min_silence_len=int(min_silence * 1000),
                silence_thresh=-40,
                keep_silence=100
            )
            if not chunks:
                continue
            novo = AudioSegment.silent(duration=0)
            for chunk in chunks:
                novo += chunk
            novo.export(caminho, format="mp3")
            count += 1

        except Exception:
            continue

    return jsonify({"status": "ok", "arquivos": count})

# @app.route("/salvar_config", methods=["POST"])
# def salvar_config():
#     import os
#     import json
#     from flask import request, jsonify
#
#     # Caminho onde o arquivo será salvo
#     config_path = os.path.join(app.root_path, "config.json")
#
#     try:
#         # Captura os dados do corpo da requisição
#         data = request.get_json()
#
#         # Salva os dados como JSON
#         with open(config_path, "w", encoding="utf-8") as f:
#             json.dump(data, f, indent=2, ensure_ascii=False)
#
#         return jsonify({"status": "ok"})
#     except Exception as e:
#         return jsonify({"status": "erro", "error": str(e)})


@app.route("/configuracoes")
def pagina_configuracoes():
    return render_template("configuracoes.html", page_title="Configurações")

@app.route("/api/configuracoes", methods=["GET"])
def obter_configuracoes():
    from modules.config import get_config
    return jsonify({
        "api_key": get_config("api_key"),
        "eleven_email": get_config("eleven_email"),
        "eleven_senha": get_config("eleven_senha"),
        "pasta_salvar": get_config("pasta_salvar")
    })

@app.route("/salvar_config", methods=["POST"])
def salvar_configuracoes():
    dados = request.get_json()
    print("📝 Config recebido do front-end:", dados)
    try:
        salvar_config(dados)
        app.config['USUARIO_CONFIG']=dados  # Atualiza em tempo real
        print("🔐 Gravado com sucesso.")
        return jsonify({"status": "ok"})
    except Exception as e:
        print("❌ Erro ao salvar config:", e)
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@app.route('/selecionar_pasta')
def selecionar_pasta():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        pasta = filedialog.askdirectory(title="Escolha a pasta de salvamento")
        root.destroy()

        if pasta:
            return jsonify({"pasta": pasta})
        else:
            return jsonify({"pasta": None})

    except Exception as e:
        return jsonify({"error": str(e), "pasta": None})


if __name__ == "__main__":
    app.run(debug=True, port=8080)
