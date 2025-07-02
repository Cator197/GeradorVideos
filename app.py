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




app = Flask(__name__)
app.config['USUARIO_CONFIG'] = carregar_config()
@app.route("/")
def index():
    """Página inicial da aplicação."""
    return render_template("generate_prompt.html", page_title="Início")

@app.route("/complete")
def complete():
    """Tela para executar o fluxo completo de geração."""
    return render_template("complete.html", page_title="Gerar Vídeo Completo")

#----- Novo prompt ----------------------------------------------------------------------------------------------------

@app.route("/generate_prompt", methods=["GET"])
def prompt_page():
    """Página para solicitar a geração de prompts."""

    return render_template("generate_prompt.html",
                           page_title="Gerar Prompt")

from modules.parser_prompts import parse_prompts_txt, salvar_prompt_txt
import re
@app.route("/processar_prompt", methods=["POST"])
def processar_prompt():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "").strip()
        nome_video = data.get("nome_video", "").strip()

        if not prompt:
            return jsonify({"status": "erro", "error": "Prompt vazio."}), 400

        if not nome_video:
            return jsonify({"status": "erro", "error": "Nome do vídeo não informado."}), 400

        # ✅ Correções automáticas
        prompt_corrigido = re.sub(r"\bimagem\b", "Imagem", prompt, flags=re.IGNORECASE)
        prompt_corrigido = re.sub(r"\bnar+ação\b", "Narração", prompt_corrigido, flags=re.IGNORECASE)
        prompt_corrigido = re.sub(r"\banima+ção\b", "Animação", prompt_corrigido, flags=re.IGNORECASE)
        prompt_corrigido = re.sub(r"\btrilha sonora\b", "Trilha Sonora", prompt_corrigido, flags=re.IGNORECASE)

        # ✅ Garante separadores ---
        blocos = [b.strip() for b in prompt_corrigido.split("---") if b.strip()]
        prompt_formatado = "\n\n---\n\n".join(blocos)

        # ✅ Salvar no prompts.txt
        salvar_prompt_txt(prompt_formatado)

        # ✅ Gerar cenas.json
        cenas = parse_prompts_txt()

        for cena in cenas:
            if "narracao" in cena and "legenda" not in cena:
                cena["legenda"] = cena["narracao"]

        # Salva o cenas.json
        cenas_path = os.path.join("modules", "cenas.json")
        with open(cenas_path, "w", encoding="utf-8") as f:
            import json
            json.dump(cenas, f, ensure_ascii=False, indent=4)

        # Salvar nome do vídeo
        with open(os.path.join("modules", "ultimo_nome_video.txt"), "w", encoding="utf-8") as f:
            f.write(nome_video)
        limpar_pastas_saida()
        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"status": "erro", "error": str(e)}), 500

#----------------------------------------------------------------------------------------------------------------------

#----- IMAGENS --------------------------------------------------------------------------------------------------------
from modules.gerar_imagens import run_gerar_imagens, calcular_indices, gerar_eventos_para_stream


@app.route("/imagens", methods=["GET"])
def imagens_page():
    path = os.path.join(app.root_path, "modules", "cenas.json")
    with open(path, encoding="utf-8") as f:
        cenas = json.load(f)

    pasta_imagens = os.path.join(get_config("pasta_salvar"), "imagens")
    arquivos = os.listdir(pasta_imagens)

    # Mapeia imagem1.jpg, imagem2.mp4 etc.
    arquivos_dict = {}
    for nome in arquivos:
        if nome.startswith("imagem") and (nome.endswith(".jpg") or nome.endswith(".png") or nome.endswith(".mp4")):
            idx = nome.replace("imagem", "").split(".")[0]
            if idx.isdigit():
                arquivos_dict[int(idx)] = nome

    return render_template("generate_imagem.html",
                           page_title="Gerar Imagens",
                           cenas=cenas,
                           arquivos_midia=arquivos_dict)



@app.route("/imagens", methods=["POST"])
def imagens_run():
    """Endpoint que inicia a geração das imagens."""
    print("[ROTA] POST /imagens")
    scope     = request.form.get("scope", "all")
    single    = request.form.get("single_index", type=int)
    start     = request.form.get("from_index", type=int)
    selected  = request.form.get("selected_indices")

    path = os.path.join(app.root_path, "modules", "cenas.json")
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    try:
        indices = calcular_indices(scope, single, start, total, selected)
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
    scope    = request.args.get("scope", "all")
    single   = request.args.get("single_index", type=int)
    start    = request.args.get("from_index", type=int)
    selected = request.args.get("selected_indices")

    return Response(
        stream_with_context(gerar_eventos_para_stream(scope, single, start, selected)),
        mimetype='text/event-stream'
    )


from modules import gerar_imagens
@app.route("/editar_prompt", methods=["POST"])
def editar_prompt():
    data = request.get_json()
    index = int(data["index"])
    novo = data["novo_prompt"]

    paths = gerar_imagens.get_paths()
    with open(paths["entrada_json"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["prompt_imagem"] = novo

    with open(paths["entrada_json"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})
import asyncio


from modules.gerar_imagens import gerar_imagens_async
@app.route("/substituir_imagem", methods=["POST"])
def substituir_imagem():
    data = request.get_json()
    index = int(data["index"])
    novo = data["novo_prompt"]

    paths = gerar_imagens.get_paths()
    with open(paths["entrada_json"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["prompt_imagem"] = novo

    # Atualiza JSON temporariamente e gera imagem
    with open(paths["entrada_json"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    logs = []
    asyncio.run(gerar_imagens_async(cenas, [index], logs))

    with open(paths["saida_json"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})

@app.route("/upload_imagem", methods=["POST"])
def upload_imagem():
    try:
        index = int(request.form["index"])
        imagem = request.files.get("imagem")
        if not imagem:
            return jsonify({"status": "erro", "msg": "Nenhum arquivo enviado"}), 400

        ext = os.path.splitext(imagem.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".mp4"]:
            return jsonify({"status": "erro", "msg": "Formato não suportado"}), 400

        paths = gerar_imagens.get_paths()
        pasta = paths["pasta_imagens"]
        os.makedirs(pasta, exist_ok=True)

        # 🗑️ Excluir arquivos antigos
        nome_base = f"imagem{index+1}"
        for old_ext in [".jpg", ".png", ".mp4"]:
            caminho_antigo = os.path.join(pasta, nome_base + old_ext)
            if os.path.exists(caminho_antigo):
                os.remove(caminho_antigo)

        # 💾 Salvar o novo
        caminho = os.path.join(pasta, nome_base + ext)
        imagem.save(caminho)

        # Atualizar JSON
        with open(paths["entrada_json"], encoding="utf-8") as f:
            cenas = json.load(f)

        cenas[index]["arquivo_local"] = caminho
        cenas[index]["image_url"] = f"/modules/imagens/{nome_base}{ext}"

        with open(paths["saida_json"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"❌ Erro em upload_imagem: {e}")
        return jsonify({"status": "erro", "msg": str(e)}), 500




#----------------------------------------------------------------------------------------------------------------------

#----- NARRAÇÃO -------------------------------------------------------------------------------------------------------
from modules.gerar_narracao import run_gerar_narracoes, iniciar_driver, login, gerar_e_baixar, get_paths
from modules import gerar_narracao

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
    start  = request.form.get("from_index", type=int)
    custom = request.form.get("custom_indices", "")
    voz    = request.form.get("voz", "Brian")
    fonte  = request.form.get("fonte", "elevenlabs")

    path = gerar_narracao.get_paths()["cenas"]
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    # Definir os índices com base no escopo
    if scope == "custom" and custom:
        try:
            indices = [int(i.strip()) - 1 for i in custom.split(",") if i.strip().isdigit()]
            indices = [i for i in indices if 0 <= i < total]
        except:
            return jsonify({"error": "Índices inválidos."}), 400
    elif scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    try:
        resultado = run_gerar_narracoes(indices, voz=voz, fonte=fonte)
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
    scope   = request.args.get("scope", "all")
    single  = request.args.get("single_index", type=int)
    start   = request.args.get("from_index", type=int)
    custom  = request.args.get("custom_indices", "")
    voz     = request.args.get("voz", "Brian")
    fonte   = request.args.get("fonte", "elevenlabs")

    path = gerar_narracao.get_paths()["cenas"]
    with open(path, encoding="utf-8") as f:
        total = len(json.load(f))

    if scope == "custom" and custom:
        try:
            indices = [int(i.strip()) - 1 for i in custom.split(",") if i.strip().isdigit()]
            indices = [i for i in indices if 0 <= i < total]
        except:
            return Response("data: ❌ Índices personalizados inválidos\n\n", mimetype='text/event-stream')
    elif scope == "all":
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
            login(driver, voz=voz)
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

@app.route("/editar_narracao", methods=["POST"])
def editar_narracao():
    data = request.get_json()
    print("🚨 Dados recebidos:", data)  # 👈 Adicione isso
    index = int(data["index"])
    novo = data["novo_texto"]


    paths = gerar_narracao.get_paths()
    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["narracao"] = novo

    with open(paths["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})

@app.route("/get_narracao")
def get_narracao():
    index = int(request.args.get("index", 0))

    paths = gerar_narracao.get_paths()

    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    texto = cenas[index].get("narracao", "")
    return jsonify({"texto": texto})


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

#----- LEGENDAS (versão .ASS) ---------------------------------------------------------------------------------------

from modules.gerar_ASS import get_paths, gerar_ass_com_whisper, carregar_modelo
from modules.config import get_config
from modules import gerar_ASS

@app.route("/generate_legenda")
def generate_legenda():
    """Página para criar legendas das narrações."""
    path = gerar_ASS.get_paths()

    with open(path["cenas"], "r", encoding="utf-8") as f:
        cenas = json.load(f)

    return render_template("generate_legenda.html", cenas=cenas)


@app.route("/legendas_ass", methods=["POST"])
def gerar_legendas_ass():
    """Gera arquivos .ASS estilizados para as cenas."""
    data = request.get_json()
    scope  = data.get("scope", "all")
    single = data.get("single_index")
    start  = data.get("from_index")

    estilo = {
        "nome": "Estilo",
        "fonte": data.get("fonte", "Arial"),
        "tamanho": int(data.get("tamanho", 48)),
        "cor": data.get("cor", "#FFFFFF"),
        "estilo": data.get("estilo", "simples"),
        "animacao": data.get("animacao", "nenhuma")
    }

    path=gerar_ASS.get_paths()

    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    total = len(cenas)
    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    logs = []
    modelo = carregar_modelo()
    modo = data.get("modo", "linha2")  # ← CORREÇÃO AQUI

    try:
        paths = gerar_ASS.get_paths()
        for idx in indices:
            path_audio = os.path.join(paths["audios"], f"narracao{idx + 1}.mp3")
            path_ass   = os.path.join(paths["legendas"], f"legenda{idx + 1}.ass")

            if not os.path.exists(path_audio):
                logs.append(f"⚠️ Áudio {idx + 1} não encontrado")
                continue

            logs.append(f"📝 Gerando legenda {idx + 1}")
            gerar_ass_com_whisper(modelo, path_audio, path_ass, estilo, modo)  # ← CORREÇÃO AQUI
            cenas[idx]["ass_path"] = path_ass
            logs.append(f"✅ Legenda {idx + 1} salva: {path_ass}")

        with open(path["cenas"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "ok", "logs": logs, "cenas": cenas})

from modules.gerar_SRT import gerar_srt_com_bloco, get_paths
from modules import gerar_SRT
@app.route("/legendas_srt", methods=["POST"])
def gerar_legendas_srt():
    data = request.get_json()
    scope = data.get("scope", "all")
    qtde_palavras = int(data.get("qtde_palavras", 4))

    single = data.get("single_index")
    start = data.get("from_index")

    with open(gerar_SRT.get_paths()["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    if scope == "single" and single is not None:
        indices = [single]
    elif scope == "from" and start is not None:
        indices = list(range(start, len(cenas)))
    else:
        indices = list(range(len(cenas)))

    resultado = gerar_srt_com_bloco(indices, qtde_palavras)
    return jsonify({"status": "ok", "logs": resultado})


@app.route("/get_legenda")
def get_legenda():
    index = int(request.args.get("index", 0))
    from modules.gerar_narracao import get_paths
    paths = gerar_ASS.get_paths()

    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    texto = cenas[index].get("legenda") or cenas[index].get("narracao", "")
    return jsonify({"texto": texto})

@app.route("/editar_legenda", methods=["POST"])
def editar_legenda():
    data = request.get_json()
    index = int(data["index"])
    novo = data["novo_texto"]


    paths = gerar_ASS.get_paths()
    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["legenda"] = novo

    with open(paths["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})



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
    """Monta os vídeos de cada cena com legenda .ASS embutida."""
    from modules.montar_cenas import run_montar_cenas

    scope   = request.form.get("scope", "all")
    single  = request.form.get("single_index", type=int)
    start   = request.form.get("from_index", type=int)

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
        resultado = run_montar_cenas(indices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "logs": resultado["logs"]
    })


@app.route("/montagem_stream", methods=["GET"])
def montagem_stream():
    """Streaming do progresso de montagem das cenas com legenda .ASS."""
    scope   = request.args.get("scope", "all")
    single  = request.args.get("single_index", type=int)
    start   = request.args.get("from_index", type=int)

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
        resultado = run_montar_cenas(indices)
        for log in resultado["logs"]:
            yield f"data: {log}\n\n"
            time.sleep(0.1)
        yield f"data: 🔚 Fim do processo\n\n"

    return Response(stream_with_context(gerar_eventos()), mimetype='text/event-stream')


#---------------------------------------------------------------------------------------------------------------------

import os, json
from flask import (
    request, render_template, jsonify,
    Response, stream_with_context, send_from_directory, send_file
)
from modules.juntar_cenas import run_juntar_cenas
from modules.config import get_config

# caminho para o JSON gerado em etapas anteriores
def caminho_cenas_final():
    return os.path.join(get_config("pasta_salvar") or ".", "cenas_com_imagens.json")

def salvar_arquivo_upload(request_file, destino):
    if request_file:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        request_file.save(destino)
        return destino
    return None

@app.route("/generate_final")
def generate_final():
    path = caminho_cenas_final()
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500
    try:
        with open(path, "r", encoding="utf-8") as f:
            cenas = json.load(f)
        return render_template("generate_final.html", cenas=cenas)
    except json.JSONDecodeError:
        return "Erro ao ler o arquivo JSON de cenas", 500


# @app.route("/finalizar", methods=["POST"])
# def finalizar_video():
#     """
#     Recebe por form-data:
#       - 'acao': 'video' ou 'capcut'
#       - 'cenas': JSON string com lista de {efeito, transicao, duracao}
#       - flags e arquivos de trilha/marca
#     """
#     try:
#         tipo = request.form.get("acao", "video")
#         cenas_json = request.form.get("cenas", "[]")
#         usar_trilha = request.form.get("usar_trilha") == "true"
#         usar_marca  = request.form.get("usar_marca")  == "true"
#
#         # salva uploads
#         trilha_path = salvar_arquivo_upload(
#             request.files.get("trilha"),
#             os.path.join(get_config("pasta_salvar"), "videos_final", "trilha.mp3")
#         ) if usar_trilha else None
#
#         marca_path = salvar_arquivo_upload(
#             request.files.get("marca"),
#             os.path.join(get_config("pasta_salvar"), "videos_final", "marca.png")
#         ) if usar_marca else None
#
#         if tipo == "video":
#             resultado = run_juntar_cenas(
#                 cenas_param=cenas_json,
#                 usar_musica=usar_trilha,
#                 trilha_path=trilha_path,
#                 volume=0.2,
#                 usar_watermark=usar_marca,
#                 marca_path=marca_path,
#                 opacidade=0.3,
#                 posicao="('right','bottom')"
#             )
#         else:
#             resultado = exportar_para_capcut(
#                 trilha_path=trilha_path,
#                 marca_path=marca_path
#             )
#
#         return jsonify(resultado)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route("/finalizar_stream", methods=["POST"])
def finalizar_stream():
    """
    Recebe JSON:
      {
        acao: "video"|"capcut",
        cenas: [{efeito, transicao, duracao}, ...],
        usar_trilha: bool,
        trilha_path?: string,
        usar_marca: bool,
        marca_path?: string
      }
    Retorna SSE (text/event-stream) com logs.
    """
    data = request.get_json(force=True)
    acao        = data.get("acao", "video")
    cenas_json  = json.dumps(data.get("cenas", []))
    usar_trilha = bool(data.get("usar_trilha"))
    trilha_path = data.get("trilha_path") if usar_trilha else None
    usar_marca  = bool(data.get("usar_marca"))
    marca_path  = data.get("marca_path")  if usar_marca  else None

    def event_gen():
        yield "data: 🚀 Iniciando montagem final...\n\n"
        # informa trilha e marca se houver
        if usar_trilha and trilha_path:
            yield f"data: 🎵 Trilha: {trilha_path}\n\n"
        if usar_marca and marca_path:
            yield f"data: 🌊 Marca d'água: {marca_path}\n\n"

        # chama o core: run_juntar_cenas ou exportar_para_capcut
        if acao == "video":
            resultado = run_juntar_cenas(
                cenas_param=cenas_json,
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

        for log in resultado.get("logs", []):
            yield f"data: {log}\n\n"
        yield "data: 🔚 Finalização concluída\n\n"

    return Response(stream_with_context(event_gen()),
                    mimetype='text/event-stream')

@app.route('/modules/videos_cenas/<path:filename>')
def serve_videos_cenas(filename):
    return send_from_directory(
        os.path.join(app.root_path, 'modules', 'videos_cenas'),
        filename
    )

@app.route('/preview_video/<int:idx>')
def preview_video(idx):
    base      = get_config("pasta_salvar") or "default"
    video_path = os.path.join(base, "videos_cenas", f"video{idx+1}.mp4")
    print(f"video{idx+1}.mp4")
    print(video_path)
    if not os.path.isfile(video_path):
        return "Vídeo não encontrado", 404
    return send_file(video_path, mimetype='video/mp4')
#--------------------------------------------------------------------------------------------------------------------

#----- COMPLETE -----------------------------------------------------------------------------------------------------
from modules.parser_prompts import  limpar_pastas_de_saida

# @app.route("/processar_prompt", methods=["POST"])
# def processar_prompt():
#     """Recebe um prompt inicial e gera o JSON de cenas."""
#     try:
#         dados=request.get_json()
#         prompt_inicial=dados.get("prompt", "").strip()
#
#         if not prompt_inicial:
#             return jsonify({"status": "erro", "erro": "Prompt vazio"}), 400
#
#         # Caminhos dos arquivos
#         BASE_DIR=os.path.dirname(os.path.abspath(__file__))
#         caminho_txt=os.path.join(BASE_DIR, "modules", "prompts.txt")
#         base=get_config("pasta_salvar") or os.getcwd()
#
#         caminho_json=os.path.join(base, "cenas.json")
#
#         # Salva o prompt no arquivo de texto
#         with open(caminho_txt, "w", encoding="utf-8") as f:
#             f.write(prompt_inicial.strip() + "\n")
#
#         # Executa o parser para gerar o JSON
#         from modules import parser_prompts
#         cenas=parser_prompts.parse_prompts_txt(caminho_txt)
#         limpar_pastas_de_saida()
#         with open(caminho_json, "w", encoding="utf-8") as f:
#             json.dump(cenas, f, ensure_ascii=False, indent=2)
#
#         return jsonify({"status": "ok", "total_cenas": len(cenas)})
#
#     except Exception as e:
#         return jsonify({"status": "erro", "erro": str(e)}), 500
#
#
# from modules import parser_prompts, gerar_imagens, gerar_narracao, gerar_SRT, juntar_cenas

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


def limpar_pastas_saida():
    pasta_base = get_config("pasta_salvar") or os.getcwd()
    subpastas = ["audios_narracoes", "imagens", "legendas_ass", "legendas_srt"]

    for subpasta in subpastas:
        pasta = os.path.join(pasta_base, subpasta)
        if os.path.exists(pasta):
            for arquivo in os.listdir(pasta):
                caminho = os.path.join(pasta, arquivo)
                if os.path.isfile(caminho):
                    os.remove(caminho)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
