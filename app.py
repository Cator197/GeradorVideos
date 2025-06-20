"""Aplicação Flask para orquestrar as etapas de geração de vídeos."""

import json
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, send_file, Response, stream_with_context
from pydub import AudioSegment, silence
from modules.config import salvar_config, carregar_config
import tkinter as tk
from tkinter import filedialog
from modules.config import get_config
import os
import time

# Importe sua função refatorada de geração de imagens

from modules.gerar_narracao import run_gerar_narracoes
from modules.gerar_SRT import run_gerar_legendas


app = Flask(__name__)
app.config['USUARIO_CONFIG'] = carregar_config()
@app.route("/")
def index():
    """Página inicial da aplicação."""
    return render_template("index.html", page_title="Início")

@app.route("/complete")
def complete():
    """Tela para executar o fluxo completo de geração."""
    return render_template("complete.html", page_title="Gerar Vídeo Completo")


#----- IMAGENS --------------------------------------------------------------------------------------------------------
from modules.gerar_imagens import run_gerar_imagens, calcular_indices, gerar_eventos_para_stream
@app.route("/imagens", methods=["GET"])
def imagens_page():
    """Página para solicitar a geração das imagens."""
    print("[ROTA] GET /imagens")
    path = os.path.join(app.root_path, "modules", "cenas.json")
    with open(path, encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_imagem.html",
                           page_title="Gerar Imagens",
                           cenas=cenas)


@app.route("/imagens", methods=["POST"])
def imagens_run():
    """Endpoint que inicia a geração das imagens."""
    print("[ROTA] POST /imagens")
    scope  = request.form.get("scope", "all")
    single = request.form.get("single_index", type=int)
    start  = request.form.get("from_index", type=int)

    path = os.path.join(app.root_path, "modules", "cenas.json")
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    try:
        indices = calcular_indices(scope, single, start, total)
        resultado = run_gerar_imagens(indices)
    except Exception as e:
        print(f"❌ Erro em /imagens: {str(e)}")
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "ok",
        "cenas": resultado["cenas"],
        "logs": resultado["logs"]
    })


@app.route("/modules/imagens/<path:filename>")
def serve_module_images(filename):
    """Retorna arquivos de imagem gerados na pasta de saída."""
    pasta_salvar = get_config("pasta_salvar")
    pasta_imagens = os.path.join(pasta_salvar, "imagens")
    return send_from_directory(pasta_imagens, filename)


@app.route("/imagens_stream", methods=["GET"])
def imagens_stream():
    """Fluxo SSE de geração de imagens."""
    print("[ROTA] GET /imagens_stream")
    scope  = request.args.get("scope", "all")
    single = request.args.get("single_index", type=int)
    start  = request.args.get("from_index", type=int)

    return Response(
        stream_with_context(gerar_eventos_para_stream(scope, single, start)),
        mimetype='text/event-stream'
    )


#----------------------------------------------------------------------------------------------------------------------

#----- NARRAÇÃO -------------------------------------------------------------------------------------------------------
from modules.gerar_narracao import run_gerar_narracoes, iniciar_driver, login, gerar_e_baixar, get_paths

@app.route("/generate_narracao")
def generate_narracao():
    """Exibe a tela de geração de narrações."""
    path = os.path.join(app.root_path, "modules", "cenas.json")
    if not os.path.exists(path):
        return "Arquivo cenas.json não encontrado", 500
    with open(path, "r", encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_narracao.html", cenas=cenas)


@app.route("/narracoes", methods=["POST"])
def narracoes_run():
    """Gera narrações para as cenas selecionadas."""
    scope  = request.form.get("scope", "all")
    single = request.form.get("single_index", type=int)
    start  = request.form.get("from_index",   type=int)

    path = get_paths()["cenas"]
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


@app.route("/narracao_stream", methods=["GET"])
def gerar_narracoes_stream():
    """Versão com feedback em tempo real das narrações."""
    scope  = request.args.get("scope", "all")
    single = request.args.get("single_index", type=int)
    start  = request.args.get("from_index", type=int)

    path = get_paths()["cenas"]
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


@app.route("/modules/audio/<path:filename>")
def serve_module_audio(filename):
    """Fornece os arquivos de áudio gerados."""
    pasta = get_paths()["audios"]
    return send_from_directory(pasta, filename)



@app.route("/remover_silencio")
def remover_silencio_route():
    """Endpoint para remover silêncios dos áudios."""
    from modules.remover_silencio import remover_silencios

    try:
        min_silence = float(request.args.get("min_silence", "0.3"))
    except ValueError:
        return jsonify({"status": "erro", "error": "Parâmetro min_silence inválido."}), 400

    resultado = remover_silencios(min_silence=min_silence)

    if resultado.get("status") == "erro":
        return jsonify(resultado), 400

    return jsonify(resultado)


#---------------------------------------------------------------------------------------------------------------------

#----- LEGENDAS ------------------------------------------------------------------------------------------------------

from modules.gerar_SRT import run_gerar_legendas, gerar_srt_por_palavra, carregar_modelo

@app.route("/generate_legenda")
def generate_legenda():
    """Página para criar legendas das narrações."""
    path = caminho_cenas_final()
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500

    with open(path, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    return render_template("generate_legenda.html", cenas=cenas)

@app.route("/legendas", methods=["POST"])
def gerar_legendas():
    """Gera arquivos de legenda para as cenas."""
    scope  = request.form.get("scope", "all")
    single = request.form.get("single_index", type=int)
    start  = request.form.get("from_index",   type=int)
    tipo   = request.form.get("tipo", "hard")

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
        from modules.gerar_SRT import run_gerar_legendas
        resultado = run_gerar_legendas(indices, tipo=tipo)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "logs": resultado["logs"],
        "cenas": resultado["cenas"]
    })

@app.route("/legendas_stream", methods=["GET"])
def gerar_legendas_stream():
    """Versão em streaming da geração de legendas."""
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
        with open(path, "r", encoding="utf-8") as f:
            cenas = json.load(f)

        for idx in indices:
            pasta_audio = os.path.join(get_config("pasta_salvar") or ".", "audios_narracoes")
            audio_path = os.path.join(pasta_audio, f"narracao{idx + 1}.mp3")

            pasta_srt = os.path.join(get_config("pasta_salvar") or ".", "legendas_srt")
            os.makedirs(pasta_srt, exist_ok=True)
            srt_path = os.path.join(pasta_srt, f"legenda{idx + 1}.srt")

            if os.path.exists(audio_path):
                yield f"data: 📝 Gerando legenda {idx + 1}\n\n"
                gerar_srt_por_palavra(carregar_modelo(), audio_path, srt_path)
                cenas[idx]["srt_path"] = srt_path
                yield f"data: ✅ Legenda {idx + 1} salva\n\n"
            else:
                yield f"data: ⚠️ Áudio {idx + 1} não encontrado\n\n"

            with open(path, "w", encoding="utf-8") as f:
                json.dump(cenas, f, ensure_ascii=False, indent=2)

        yield f"data: 🔚 Fim do processo\n\n"

    return Response(stream_with_context(gerar_eventos()), mimetype='text/event-stream')

#---------------------------------------------------------------------------------------------------------------------


#----- MONTAR CENAS --------------------------------------------------------------------------------------------------

@app.route("/generate_montagem")
def generate_montagem():
    """Renderiza a página para montar vídeos das cenas."""
    path = caminho_cenas_final()
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500
    with open(path, "r", encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_montagem.html", cenas=cenas)

@app.route("/montagem", methods=["POST"])
def montagem_cenas():
    """Monta os vídeos de cada cena de acordo com as opções."""
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

@app.route("/montagem_stream", methods=["GET"])
def montagem_stream():
    """Streaming do progresso de montagem das cenas."""
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


#---------------------------------------------------------------------------------------------------------------------

#----- EDIDAR UNIR ---------------------------------------------------------------------------------------------------
from modules.juntar_cenas import run_juntar_cenas, exportar_para_capcut

def caminho_cenas_final():
    """Caminho do arquivo JSON contendo as cenas com imagens."""
    return os.path.join(get_config("pasta_salvar") or ".", "cenas_com_imagens.json")


def salvar_arquivo_upload(request_file, destino):
    """Persiste arquivos enviados pelo usuário em ``destino``."""
    if request_file:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        request_file.save(destino)
        return destino
    return None


@app.route("/generate_final")
def generate_final():
    """Página para escolher a junção final dos vídeos."""
    path = caminho_cenas_final()
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500
    try:
        with open(path, "r", encoding="utf-8") as f:
            cenas = json.load(f)
        return render_template("generate_final.html", cenas=cenas)
    except json.JSONDecodeError:
        return "Erro ao ler o arquivo JSON de cenas", 500


@app.route("/finalizar", methods=["POST"])
def finalizar_video():
    """Une as cenas ou gera projeto para edição."""
    try:
        tipo = request.form.get("acao", "video")
        transicao = request.form.get("transicao", "cut")
        usar_trilha = request.form.get("usar_trilha") == "true"
        usar_marca = request.form.get("usar_marca") == "true"

        trilha_path = salvar_arquivo_upload(
            request.files.get("trilha"),
            os.path.join(get_config("pasta_salvar"), "videos_final", "trilha.mp3")
        ) if usar_trilha else None

        marca_path = salvar_arquivo_upload(
            request.files.get("marca"),
            os.path.join(get_config("pasta_salvar"), "videos_final", "marca.png")
        ) if usar_marca else None

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
                trilha_path=trilha_path,
                marca_path=marca_path
            )

        return jsonify(resultado)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/finalizar_stream", methods=["GET"])
def finalizar_stream():
    """Versão em streaming da finalização do vídeo."""
    try:
        tipo = request.args.get("acao", "video")
        transicao = request.args.get("transicao", "cut")
        usar_trilha = request.args.get("usar_trilha") == "true"
        usar_marca = request.args.get("usar_marca") == "true"

        trilha_path = None
        marca_path = None

        def gerar_eventos():
            yield f"data: 🚀 Iniciando montagem final...\n\n"

            trilha_path_param = request.args.get("trilha_path")
            if usar_trilha and trilha_path_param and os.path.isfile(trilha_path_param):
                yield f"data: 🎵 Usando trilha: {trilha_path_param}\n\n"
                nonlocal trilha_path
                trilha_path = trilha_path_param

            marca_path_param = request.args.get("marca_path")
            if usar_marca and marca_path_param and os.path.isfile(marca_path_param):
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
                    trilha_path=trilha_path,
                    marca_path=marca_path
                )

            for linha in resultado.get("logs", []):
                yield f"data: {linha}\n\n"

            yield f"data: 🔚 Finalização concluída\n\n"

        return Response(stream_with_context(gerar_eventos()), mimetype='text/event-stream')

    except Exception as e:
        return Response(f"data: ❌ Erro: {str(e)}\n\n", mimetype='text/event-stream')


@app.route('/modules/videos_cenas/<path:filename>')
def serve_videos_cenas(filename):
    """Serve arquivos de vídeo das cenas individuais."""
    return send_from_directory(
        os.path.join(app.root_path, 'modules', 'videos_cenas'),
        filename
    )


@app.route('/preview_video/<int:idx>')
def preview_video(idx):
    """Exibe um vídeo de cena para pré-visualização."""
    base_path = get_config("pasta_salvar") or "default"
    video_path = os.path.join(base_path, "videos_cenas", f"video{idx}.mp4")

    if not os.path.isfile(video_path):
        return "Vídeo não encontrado", 404

    return send_file(video_path, mimetype='video/mp4')

#--------------------------------------------------------------------------------------------------------------------

#----- COMPLETE -----------------------------------------------------------------------------------------------------
from modules.parser_prompts import  limpar_pastas_de_saida
@app.route("/processar_prompt", methods=["POST"])
def processar_prompt():
    """Recebe um prompt inicial e gera o JSON de cenas."""
    try:
        dados=request.get_json()
        prompt_inicial=dados.get("prompt", "").strip()

        if not prompt_inicial:
            return jsonify({"status": "erro", "erro": "Prompt vazio"}), 400

        # Caminhos dos arquivos
        BASE_DIR=os.path.dirname(os.path.abspath(__file__))
        caminho_txt=os.path.join(BASE_DIR, "modules", "prompts.txt")
        base=get_config("pasta_salvar") or os.getcwd()

        caminho_json=os.path.join(base, "cenas.json")

        # Salva o prompt no arquivo de texto
        with open(caminho_txt, "w", encoding="utf-8") as f:
            f.write(prompt_inicial.strip() + "\n")

        # Executa o parser para gerar o JSON
        from modules import parser_prompts
        cenas=parser_prompts.parse_prompts_txt(caminho_txt)
        limpar_pastas_de_saida()
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok", "total_cenas": len(cenas)})

    except Exception as e:
        return jsonify({"status": "erro", "erro": str(e)}), 500


from modules import parser_prompts, gerar_imagens, gerar_narracao, gerar_SRT, juntar_cenas

@app.route("/complete_stream")
def complete_stream():
    """Executa toda a pipeline de geração enviando logs por SSE."""
    from modules import parser_prompts, gerar_imagens, gerar_narracao, gerar_SRT, montar_cenas, juntar_cenas

    def gerar_log():
        try:
            # 📥 Parâmetros do front
            prompt           = request.args.get("prompt", "").strip()
            nome_video       = request.args.get("nome_video", "video_final").strip()
            usar_legenda     = request.args.get("usar_legenda", "false") == "true"
            tipo_legenda     = request.args.get("tipo_legenda", "hard")
            cor              = request.args.get("cor_legenda", "white")
            tamanho          = int(request.args.get("tamanho_legenda", 24))
            posicao          = request.args.get("posicao_legenda", "bottom")
            usar_marca       = request.args.get("usar_marca", "false") == "true"
            usar_trilha      = request.args.get("usar_trilha", "false") == "true"
            exportar_capcut  = request.args.get("exportar_capcut", "false") == "true"
            unir_videos      = request.args.get("unir_videos", "false") == "true"
            voz              = request.args.get("voz", "Brian")
            engine           = request.args.get("tts_engine", "eleven")

            if not prompt:
                yield "data: ❌ Prompt inicial vazio\n\n"
                return

            # 🔹 Etapa 1: Processar prompt
            yield "data: 🧠 Processando prompt inicial...\n\n"
            parser_prompts.salvar_prompt_txt(prompt)
            parser_prompts.limpar_pastas()
            cenas = parser_prompts.parse_prompts_txt()
            with open(get_config("pasta_salvar") + "/cenas_com_imagens.json", "w", encoding="utf-8") as f:
                json.dump(cenas, f, ensure_ascii=False, indent=2)
            yield f"data: ✅ {len(cenas)} prompts processados\n\n"

            indices = list(range(len(cenas)))

            # 🔹 Etapa 2: Gerar imagens
            yield "data: 🎨 Gerando imagens...\n\n"
            resultado_imagens = gerar_imagens.run_gerar_imagens(indices)
            for log in resultado_imagens["logs"]:
                yield f"data: {log}\n\n"

            # 🔹 Etapa 3: Gerar narrações
            yield "data: 🎙️ Gerando narrações...\n\n"
            resultado_audio = gerar_narracao.run_gerar_narracoes(indices)
            for log in resultado_audio["logs"]:
                yield f"data: {log}\n\n"

            # 🔹 Etapa 4: Gerar legendas
            if usar_legenda:
                yield f"data: 💬 Gerando legendas ({tipo_legenda})...\n\n"
                resultado_legendas = gerar_SRT.run_gerar_legendas(indices, tipo=tipo_legenda)
                for log in resultado_legendas["logs"]:
                    yield f"data: {log}\n\n"

            # 🔹 Etapa 5: Montar vídeos das cenas
            yield "data: 🧩 Montando cenas...\n\n"
            resultado_montagem = montar_cenas.run_montar_cenas(indices, usar_soft=(tipo_legenda=="soft"), cor=cor, tamanho=tamanho, posicao=posicao)
            for log in resultado_montagem["logs"]:
                yield f"data: {log}\n\n"

            # 🔹 Etapa 6: Juntar vídeo final
            if unir_videos:
                yield "data: 🎞️ Juntando vídeo final...\n\n"
                resultado_final = juntar_cenas.run_juntar_cenas(
                    tipo_transicao="cut",
                    usar_musica=usar_trilha,
                    trilha_path=os.path.join(get_config("pasta_salvar"), "videos_final", "trilha.mp3") if usar_trilha else None,
                    volume=0.2,
                    usar_watermark=usar_marca,
                    marca_path=os.path.join(get_config("pasta_salvar"), "videos_final", "marca.png") if usar_marca else None,
                    opacidade=0.3,
                    posicao="('right','bottom')"
                )
                for log in resultado_final["logs"]:
                    yield f"data: {log}\n\n"



            yield "data: ✅ Pipeline completa finalizada\n\n"

        except Exception as e:
            yield f"data: ❌ Erro: {str(e)}\n\n"

    return Response(stream_with_context(gerar_log()), mimetype='text/event-stream')


#--------------------------------------------------------------------------------------------------------------------

#----- CONFIGURAÇÕES ------------------------------------------------------------------------------------------------

@app.route("/configuracoes")
def pagina_configuracoes():
    """Exibe a tela de configurações do usuário."""
    return render_template("configuracoes.html", page_title="Configurações")

@app.route("/api/configuracoes", methods=["GET"])
def obter_configuracoes():
    """Retorna as configurações atuais em formato JSON."""
    from modules.config import get_config
    return jsonify({
        "api_key": get_config("api_key"),
        "eleven_email": get_config("eleven_email"),
        "eleven_senha": get_config("eleven_senha"),
        "pasta_salvar": get_config("pasta_salvar")
    })

@app.route("/salvar_config", methods=["POST"])
def salvar_configuracoes():
    """Persiste as configurações enviadas pelo frontend."""
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
    """Abre diálogo para o usuário escolher uma pasta local."""
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
    app.run(debug=True, port=5000)
