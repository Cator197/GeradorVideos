"""Aplicação Flask para orquestrar as etapas de geração de vídeos."""
import hashlib
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, send_file, Response, stream_with_context
import tkinter as tk
from tkinter import filedialog
from modules.config import salvar_config, carregar_config, get_config
from modules.parser_prompts import parse_prompts_txt, salvar_prompt_txt
from modules.gerar_imagens import run_gerar_imagens, calcular_indices, gerar_eventos_para_stream, gerar_imagens_async
from modules.gerar_narracao import iniciar_driver, login, gerar_e_baixar
from modules.gerar_ASS import gerar_ass_com_whisper, carregar_modelo
from modules.gerar_SRT import gerar_srt_com_bloco, unir_srt
from modules.paths import get_paths
import re, os, json, asyncio, time, subprocess, threading, sys
from modules.juntar_cenas import montar_uma_cena, adicionar_trilha_sonora, adicionar_marca_dagua, unir_cenas_com_transicoes
from modules.verify_license import verify_license
from werkzeug.utils import secure_filename
from modules.licenca import get_creditos
from modules.licenca import (
    carregar_fernet, ler_estado_creditos, salvar_estado_creditos,
    ler_shadow_serial, gravar_shadow_serial, get_hardware_id
)
from modules.verify_license import load_public_key
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from datetime import datetime


path = get_paths()

estado_pausa = {
    "pausado": False,
    "cond": threading.Condition()
}

app = Flask(__name__)
app.config['USUARIO_CONFIG'] = carregar_config()

@app.route("/")
def index():
    """Página inicial da aplicação."""
    return render_template("generate_prompt.html", page_title="Início")

#----- Novo prompt ----------------------------------------------------------------------------------------------------

@app.route("/generate_prompt", methods=["GET"])
def prompt_page():
    """Página para solicitar a geração de prompts."""

    return render_template("generate_prompt.html",
                           page_title="Gerar Prompt")

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
        with open(path["cenas"], "w", encoding="utf-8") as f:
            import json
            json.dump(cenas, f, ensure_ascii=False, indent=4)

        # Salvar nome do vídeo
        with open(path["nome_video"], "w", encoding="utf-8") as f:
            f.write(nome_video)
        limpar_pastas_saida()
        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"status": "erro", "error": str(e)}), 500

#----------------------------------------------------------------------------------------------------------------------

#----- IMAGENS --------------------------------------------------------------------------------------------------------

@app.route("/imagens", methods=["GET"])
def imagens_page():
    # Carrega as cenas
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    # Garante que a pasta de imagens existe
    os.makedirs(path["imagens"], exist_ok=True)

    arquivos = os.listdir(path["imagens"])

    # Mapeia os arquivos existentes para cada imagem
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
    #("[ROTA] POST /imagens")
    scope     = request.form.get("scope", "all")
    single    = request.form.get("single_index", type=int)
    start     = request.form.get("from_index", type=int)
    selected  = request.form.get("selected_indices")

    #path = os.path.join(os.getcwd(),"cenas.json")
    with open(path["cenas"], encoding="utf-8") as f:
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
    # pasta_salvar = get_config("pasta_salvar")
    # pasta_imagens = os.path.join(pasta_salvar, "imagens")
    return send_from_directory(path["imagens"], filename)

@app.route("/imagens_stream", methods=["GET"])
def imagens_stream():
    """Fluxo SSE de geração de imagens."""
    #print("[ROTA] GET /imagens_stream")
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

    #paths = gerar_imagens.get_paths()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["prompt_imagem"] = novo

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})

@app.route("/substituir_imagem", methods=["POST"])
def substituir_imagem():
    data = request.get_json()
    index = int(data["index"])
    novo = data["novo_prompt"]

    #paths = gerar_imagens.get_paths()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["prompt_imagem"] = novo

    # Atualiza JSON temporariamente e gera imagem
    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    logs = []
    asyncio.run(gerar_imagens_async(cenas, [index], logs))

    with open(path["cenas"], "w", encoding="utf-8") as f:
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

        # paths = gerar_imagens.get_paths()
        # pasta = paths["pasta_imagens"]
        os.makedirs(path["imagens"], exist_ok=True)

        # 🗑️ Excluir arquivos antigos
        nome_base = f"imagem{index+1}"
        for old_ext in [".jpg", ".png", ".mp4"]:
            caminho_antigo = os.path.join(path["imagens"], nome_base + old_ext)
            if os.path.exists(caminho_antigo):
                os.remove(caminho_antigo)

        # 💾 Salvar o novo
        caminho = os.path.join(path["imagens"], nome_base + ext)
        imagem.save(caminho)

        # Atualizar JSON
        with open(path["cenas"], encoding="utf-8") as f:
            cenas = json.load(f)

        cenas[index]["arquivo_local"] = caminho
        cenas[index]["image_url"] = f"/modules/imagens/{nome_base}{ext}"

        with open(path["cenas"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"❌ Erro em upload_imagem: {e}")
        return jsonify({"status": "erro", "msg": str(e)}), 500

@app.route("/cenas/adicionar", methods=["POST"])
def cenas_adicionar():
    """
    Cria uma nova cena (append) OU vincula prompt a uma cena existente.
    Se gerar_imagem=True, já dispara a geração para o índice escolhido.
    Body (JSON):
      - modo: "novo" | "existente"
      - narracao?: str              (obrigatório se modo=novo)
      - legenda?: str               (opcional; se faltar = narracao)
      - index?: int                 (obrigatório se modo=existente; base 1)
      - prompt_imagem?: str         (opcional no novo; recomendado)
      - gerar_imagem?: bool
    """
    data = request.get_json(silent=True) or {}
    modo = (data.get("modo") or "").strip().lower()
    gerar = bool(data.get("gerar_imagem", False))

    # Carrega cenas atuais
    if not os.path.exists(path["cenas"]):
        return jsonify({"status": "erro", "msg": "cenas.json não encontrado"}), 500
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    novo_index = None

    if modo == "novo":
        narracao = (data.get("narracao") or "").strip()
        if not narracao:
            return jsonify({"status": "erro", "msg": "narracao é obrigatória no modo=novo"}), 400

        prompt_imagem = (data.get("prompt_imagem") or "").strip()
        legenda = (data.get("legenda") or narracao).strip()

        nova_cena = {
            "narracao": narracao,
            "legenda": legenda,
            "prompt_imagem": prompt_imagem,
            "audio_path": None,
            "srt_path": None,
            "ass_path": None,
            "arquivo_local": None,
            "image_url": None,
            "task_id_imagem": None
        }
        cenas.append(nova_cena)
        novo_index = len(cenas) - 1

        # Persiste a criação
        with open(path["cenas"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        # Se pediu para gerar, dispara agora
        if gerar:
            logs = []
            try:
                asyncio.run(gerar_imagens_async(cenas, [novo_index], logs))
            finally:
                # Garante que o estado pós-geração ficou salvo no cenas.json
                with open(path["cenas"], "w", encoding="utf-8") as f:
                    json.dump(cenas, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok", "index": novo_index + 1})

    elif modo == "existente":
        try:
            idx1 = int(data.get("index"))
        except Exception:
            return jsonify({"status": "erro", "msg": "index inválido"}), 400
        idx0 = idx1 - 1
        if not (0 <= idx0 < len(cenas)):
            return jsonify({"status": "erro", "msg": "index fora do range"}), 400

        # Atualiza prompt (se enviado)
        if "prompt_imagem" in data:
            cenas[idx0]["prompt_imagem"] = (data.get("prompt_imagem") or "").strip()

        with open(path["cenas"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        if gerar:
            logs = []
            try:
                asyncio.run(gerar_imagens_async(cenas, [idx0], logs))
            finally:
                with open(path["cenas"], "w", encoding="utf-8") as f:
                    json.dump(cenas, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok", "index": idx1})

    else:
        return jsonify({"status": "erro", "msg": "modo deve ser 'novo' ou 'existente'"}), 400

@app.route("/cenas/adicionar_upload", methods=["POST"])
def cenas_adicionar_upload():
    """
    Cria uma cena nova ou vincula a existente salvando o arquivo enviado.
    Form-data:
      - modo: "novo" | "existente"
      - index?: int (base 1; obrigatório se existente)
      - narracao?: str (obrigatório se novo)
      - legenda?: str (opcional se novo)
      - arquivo: file (.jpg/.jpeg/.png/.mp4)
    """
    try:
        modo = (request.form.get("modo") or "").strip().lower()
        arquivo = request.files.get("arquivo")
        if not arquivo:
            return jsonify({"status": "erro", "msg": "Nenhum arquivo enviado"}), 400

        ext = os.path.splitext(arquivo.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".mp4"]:
            return jsonify({"status": "erro", "msg": "Formato não suportado"}), 400

        # Carrega cenas
        if not os.path.exists(path["cenas"]):
            return jsonify({"status": "erro", "msg": "cenas.json não encontrado"}), 500
        with open(path["cenas"], encoding="utf-8") as f:
            cenas = json.load(f)

        os.makedirs(path["imagens"], exist_ok=True)

        if modo == "novo":
            narracao = (request.form.get("narracao") or "").strip()
            if not narracao:
                return jsonify({"status": "erro", "msg": "narracao é obrigatória no modo=novo"}), 400
            legenda = (request.form.get("legenda") or narracao).strip()

            nova_cena = {
                "narracao": narracao,
                "legenda": legenda,
                "prompt_imagem": "",
                "audio_path": None,
                "srt_path": None,
                "ass_path": None,
                "arquivo_local": None,
                "image_url": None,
                "task_id_imagem": None
            }
            cenas.append(nova_cena)
            idx0 = len(cenas) - 1  # zero-based
            idx1 = idx0 + 1

        elif modo == "existente":
            try:
                idx1 = int(request.form.get("index"))
            except Exception:
                return jsonify({"status": "erro", "msg": "index inválido"}), 400
            idx0 = idx1 - 1
            if not (0 <= idx0 < len(cenas)):
                return jsonify({"status": "erro", "msg": "index fora do range"}), 400
        else:
            return jsonify({"status": "erro", "msg": "modo deve ser 'novo' ou 'existente'"}), 400

        # Remove arquivos antigos desse índice
        nome_base = f"imagem{idx1}"
        for old_ext in [".jpg", ".jpeg", ".png", ".mp4"]:
            caminho_antigo = os.path.join(path["imagens"], nome_base + old_ext)
            if os.path.exists(caminho_antigo):
                try:
                    os.remove(caminho_antigo)
                except Exception as e:
                    print(f"⚠️ Erro ao remover {caminho_antigo}: {e}")

        # Salva o novo
        caminho = os.path.join(path["imagens"], nome_base + ext)
        arquivo.save(caminho)

        # Atualiza a cena
        cenas[idx0]["arquivo_local"] = caminho
        cenas[idx0]["image_url"] = f"/modules/imagens/{nome_base}{ext}"

        with open(path["cenas"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok", "index": idx1})

    except Exception as e:
        print(f"❌ Erro em /cenas/adicionar_upload: {e}")
        return jsonify({"status": "erro", "msg": str(e)}), 500



@app.route("/api/creditos")
def api_creditos():

    return {"creditos": get_creditos()}


#----------------------------------------------------------------------------------------------------------------------

#----- NARRAÇÃO -------------------------------------------------------------------------------------------------------

@app.route("/generate_narracao")
def generate_narracao():
    """Exibe a tela de geração de narrações."""
    #path = os.path.join(os.getcwd(),"cenas.json")
    if not os.path.exists(path["cenas"]):
        return "Arquivo cenas.json não encontrado", 500
    with open(path["cenas"], "r", encoding="utf-8") as f:
        cenas = json.load(f)
    return render_template("generate_narracao.html",page_title="Gerar Narração", cenas=cenas)
# @app.route("/narracoes", methods=["POST"])
# def narracoes_run():
#     """Gera narrações para as cenas selecionadas."""
#     scope  = request.form.get("scope", "all")
#     single = request.form.get("single_index", type=int)
#     start  = request.form.get("from_index", type=int)
#     custom = request.form.get("custom_indices", "")
#     voz    = request.form.get("voz", "Brian")
#     fonte  = request.form.get("fonte", "elevenlabs")
#
#     path = gerar_narracao.get_paths()["cenas"]
#     with open(path, encoding="utf-8") as f:
#         total = len(json.load(f))
#
#     # Definir os índices com base no escopo
#     if scope == "custom" and custom:
#         try:
#             indices = [int(i.strip()) - 1 for i in custom.split(",") if i.strip().isdigit()]
#             indices = [i for i in indices if 0 <= i < total]
#         except:
#             return jsonify({"error": "Índices inválidos."}), 400
#     elif scope == "all":
#         indices = list(range(total))
#     elif scope == "single" and single and 1 <= single <= total:
#         indices = [single - 1]
#     elif scope == "from" and start and 1 <= start <= total:
#         indices = list(range(start - 1, total))
#     else:
#         return jsonify({"error": "Parâmetros inválidos"}), 400
#
#     try:
#         resultado = run_gerar_narracoes(indices, voz=voz, fonte=fonte)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#
#     return jsonify({
#         "status": "ok",
#         "logs": resultado["logs"],
#         "cenas": resultado["cenas"]
#     })
@app.route("/narracao_stream", methods=["GET"])
def gerar_narracoes_stream():
    """Versão com feedback em tempo real das narrações."""
    scope   = request.args.get("scope", "all")
    single  = request.args.get("single_index", type=int)
    start   = request.args.get("from_index", type=int)
    custom  = request.args.get("custom_indices", "")
    voz     = request.args.get("voz", "Brian")
    fonte   = request.args.get("fonte", "elevenlabs")

    # path = gerar_narracao.get_paths()["cenas"]
    with open(path["cenas"], encoding="utf-8") as f:
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
        with open(path["cenas"], encoding="utf-8") as f:
            cenas = json.load(f)

        yield f"data: 🚀 Iniciando geração de narrações...\n\n"
        driver = iniciar_driver()
        try:
            login(driver, voz=voz)
            #--------------confirmar se a pausa é aqui----------------
            if estado_pausa["pausado"]:
                yield f"data: ⏸️ Pausado . Aguarde liberação do usuário.\n\n"
                with estado_pausa["cond"]:
                    estado_pausa["cond"].wait()

            for i in indices:
                texto = cenas[i].get("narracao")
                if not texto:
                    yield f"data: ⚠️ Cena {i+1} sem texto.\n\n"
                    continue

                yield f"data: 🎙️ Gerando narração {i+1}\n\n"
                path_audio = gerar_e_baixar(driver, texto, i)
                cenas[i]["audio_path"] = path_audio
                yield f"data: ✅ Narração {i+1} salva\n\n"

                with open(path["cenas"], "w", encoding="utf-8") as f:
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
    return send_from_directory(path["audios"], filename)

@app.route("/editar_narracao", methods=["POST"])
def editar_narracao():
    data = request.get_json()
    #print("🚨 Dados recebidos:", data)  # 👈 Adicione isso
    index = int(data["index"])
    novo = data["novo_texto"]

    #paths = gerar_narracao.get_paths()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["narracao"] = novo

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})

@app.route("/get_narracao")
def get_narracao():
    index = int(request.args.get("index", 0))

    #paths = gerar_narracao.get_paths()

    with open(path["cenas"], encoding="utf-8") as f:
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

@app.route("/ativar_pausa", methods=["POST"])
def ativar_pausa():
    with estado_pausa["cond"]:
        estado_pausa["pausado"] = True
    return jsonify({"status": "ok"})

@app.route("/continuar_narracao", methods=["POST"])
def continuar_narracao():
    with estado_pausa["cond"]:
        estado_pausa["pausado"] = False
        estado_pausa["cond"].notify()
    return jsonify({"status": "ok"})

#---------------------------------------------------------------------------------------------------------------------

#----- LEGENDAS (versão .ASS) ---------------------------------------------------------------------------------------

@app.route("/generate_legenda")
def generate_legenda():
    """Página para criar legendas das narrações."""
    #path = os.path.join(os.getcwd(),"cenas.json")

    with open(path["cenas"], "r", encoding="utf-8") as f:
        cenas = json.load(f)

    return render_template("generate_legenda.html", page_title="Gerar Legendas", cenas=cenas)

@app.route("/legendas_ass", methods=["POST"])
def gerar_legendas_ass():
    """Gera arquivos .ASS estilizados para as cenas."""
    data = request.get_json()
    scope  = data.get("scope", "all")
    single = data.get("single_index")
    start  = data.get("from_index")

    estilo={
        "fonte": data.get("fonte", "Arial"),
        "tamanho": int(data.get("tamanho", 48)),
        "estilo": data.get("estilo", "simples"),
        "animacao": data.get("animacao", "nenhuma"),
        "cor_primaria": data.get("cor_primaria"),
        "cor_secundaria": data.get("cor_secundaria", "#00FFFF"),
        "cor_outline": data.get("cor_outline", "#000000"),
        "cor_back": data.get("cor_back", "#000000")  # mesmo campo usado
    }

    #path=gerar_ASS.get_paths()

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
        #paths = gerar_ASS.get_paths()
        for idx in indices:
            path_audio = os.path.join(path["audios"], f"narracao{idx+1}.mp3")
            path_ass   = os.path.join(path["legendas_ass"], f"legenda{idx+1}.ass")

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

from flask import jsonify, request

def _as_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

@app.route("/legendas_srt", methods=["POST"])
def gerar_legendas_srt():
    # Gera SRTs por cena -> usa índices base-0
    data = request.get_json(silent=True) or {}
    scope = data.get("scope", "all")
    qtde_palavras = _as_int(data.get("qtde_palavras")) or 4

    single = _as_int(data.get("single_index"))   # pode vir como str
    start  = _as_int(data.get("from_index"))     # pode vir como str

    # (Opcional) obtem paths dinamicamente se preferir evitar variáveis globais
    # path = get_paths()

    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    n = len(cenas)

    if scope == "single" and single is not None:
        # single como índice de cena (base-0). Se seu front manda 1-based, troque para: single = single - 1
        idx0 = _clamp(single, 0, n - 1)
        indices = [idx0]
    elif scope == "from" and start is not None:
        # 'from' como índice de cena (base-0). Se seu front manda 1-based, troque para: start = start - 1
        start0 = _clamp(start, 0, n - 1)
        indices = list(range(start0, n))  # inclui até n-1
    else:
        # all -> todas as cenas base-0
        indices = list(range(0, n))

    resultado = gerar_srt_com_bloco(indices, qtde_palavras)
    return jsonify({"status": "ok", "logs": resultado})


@app.route("/merge_legendas_srt", methods=["POST"])
def merge_legendas_srt():
    # Une SRTs por arquivo -> usa IDs base-1 (legenda1.srt ... legendaN.srt)
    data = request.get_json(silent=True) or {}
    scope  = data.get("scope", "all")
    single = _as_int(data.get("single_index"))
    start  = _as_int(data.get("from_index"))

    try:
        with open(path["cenas"], encoding="utf-8") as f:
            cenas = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "Arquivo de cenas não encontrado.", "logs": []}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Erro ao ler o arquivo de cenas.", "logs": []}), 500

    total = len(cenas)

    if scope == "single" and single is not None:
        # single aqui é ID base-1 (legenda{single}.srt). Se seu front manda 0-based, use: single = single + 1
        id1 = _clamp(single, 1, total)
        indices = [id1]
    elif scope == "from" and start is not None:
        # from aqui é ID base-1 (legenda{start}.srt). Se seu front manda 0-based, use: start = start + 1
        start1 = _clamp(start, 1, total)
        indices = list(range(start1, total + 1))  # inclui o último (total)
    else:
        # all -> 1..total
        indices = list(range(1, total + 1))

    resultado = unir_srt(indices)
    logs = resultado.get("logs", [])

    if resultado.get("error"):
        status = resultado.get("status", 400)
        return jsonify({"error": resultado["error"], "logs": logs}), status

    resposta = {
        "logs": logs,
        "message": resultado.get("message", "Legendas SRT unidas com sucesso."),
    }
    if resultado.get("output"):
        resposta["output"] = resultado["output"]

    return jsonify(resposta)


@app.route("/get_legenda")
def get_legenda():
    index = int(request.args.get("index", 0))
    from modules.gerar_narracao import get_paths
    #paths = gerar_ASS.get_paths()

    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    texto = cenas[index].get("legenda") or cenas[index].get("narracao", "")
    return jsonify({"texto": texto})

@app.route("/editar_legenda", methods=["POST"])
def editar_legenda():
    data = request.get_json()
    index = int(data["index"])
    novo = data["novo_texto"]


    #paths = gerar_ASS.get_paths()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    cenas[index]["legenda"] = novo

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})

@app.route("/verificar_legendas_ass")
def verificar_legendas_ass():
    from glob import glob
    from modules.paths import get_paths
    import os

    legenda_dir = get_paths()["legendas_ass"]
    arquivos = glob(os.path.join(legenda_dir, "*.ass"))
    return jsonify({"tem": bool(arquivos)})


#---------------------------------------------------------------------------------------------------------------------

@app.route("/generate_final")
def generate_final():
    path = caminho_cenas_final()
    if not os.path.exists(path):
        return "Arquivo cenas_com_imagens.json não encontrado", 500
    try:
        with open(path, "r", encoding="utf-8") as f:
            cenas = json.load(f)
        return render_template("generate_final.html", page_title="Gerar Video Final", cenas=cenas)
    except json.JSONDecodeError:
        return "Erro ao ler o arquivo JSON de cenas", 500

@app.route("/montar_cenas_stream", methods=["GET"])
def montar_cenas_stream():
    scope   = request.args.get("scope", "all")
    single  = request.args.get("single_index", type=int)
    start   = request.args.get("from_index", type=int)
    print(f"📥 scope={scope} | single={single} | from={start}")
    #path = caminho_cenas_final()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas_json = json.load(f)
        total = len(cenas_json)

    print("o cenas json esta em: ", path["cenas"])
    print(cenas_json)
    print(f"📥 scope={scope} | single={single} | from={start}")
    if scope == "all":
        indices = list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        indices = [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        indices = list(range(start - 1, total))
    else:
        return Response("data: ❌ Parâmetros inválidos\n\n", mimetype='text/event-stream')

    def gerar():
        yield "data: 🚀 Iniciando geração das cenas individuais...\n\n"
        logs = []
        for idx in indices:
            try:
                config = cenas_json[idx]
                print(cenas_json)
                print(cenas_json[idx])


                caminho = montar_uma_cena(idx, config)
                print("chegou aqui")
                logs.append(f"✅ Cena {idx + 1} salva em {os.path.basename(caminho)}")
                yield f"data: ✅ Cena {idx + 1} gerada com sucesso\n\n"
            except Exception as e:
                logs.append(f"❌ Erro na cena {idx + 1}: {str(e)}")
                yield f"data: ❌ Erro na cena {idx + 1}: {str(e)}\n\n"
                yield f"data: ⚠️ Config usada: {json.dumps(cenas_json[idx], indent=2)}\n\n"
        yield "data: 🔚 Conclusão das cenas\n\n"

    return Response(stream_with_context(gerar()), mimetype='text/event-stream')

@app.route("/atualizar_config_cenas", methods=["POST"])
def atualizar_config_cenas():
    cenas_config = request.get_json()
    #path = caminho_cenas_final()
    with open(path["cenas"], encoding="utf-8") as f:
        cenas_existentes = json.load(f)

    for i, cena in enumerate(cenas_config):
        cenas_existentes[i].update(cena)

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas_existentes, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "ok"})

@app.route("/finalizar_stream", methods=["POST"])
def finalizar_stream():
    try:
        # 📥 Parâmetros recebidos
        escopo = request.form.get("escopo", "all")
        idx_str = request.form.get("idx", "")
        idx = int(idx_str) - 1 if idx_str.isdigit() else 0
        transicoes = json.loads(request.form.get("transicoes", "[]"))

        usar_trilha = request.form.get("usar_trilha") == "true"
        trilha_file = request.files.get("trilha")
        volume_pct = int(request.form.get("volume_trilha", 100))
        volume = max(0.0, min(volume_pct / 100.0, 1.0))

        usar_marca = request.form.get("usar_marca") == "true"
        marca_file = request.files.get("marca")
        opacidade_pct = int(request.form.get("opacidade_marca", 100))
        opacidade = max(0.0, min(opacidade_pct / 100.0, 1.0))

        # 📁 Pastas?

        os.makedirs(path["videos_final"], exist_ok=True)

        # 🎬 Arquivos a unir
        if escopo == "single":
            arquivos = [os.path.join(path["videos_cenas"], f"video{idx + 1}.mp4")]
        else:
            arquivos = sorted([
                os.path.join(path["videos_cenas"], f) for f in os.listdir(path["videos_cenas"])
                if f.startswith("video") and f.endswith(".mp4")
            ], key=lambda x: int(re.search(r'video(\d+)', x).group(1)))

        print("🎬 Cenas encontradas:", arquivos)

        # 🧩 Etapa 1: Unir cenas com transições
        # 📄 Nome do vídeo final vindo do txt
        try:
            with open("ultimo_nome_video.txt", encoding="utf-8") as f:
                nome_video=f.read().strip()
            nome_arquivo=f"{nome_video}.mp4"
        except Exception:
            nome_arquivo="video_final.mp4"  # fallback
            print("⚠️ Não foi possível ler o nome do vídeo, usando padrão.")

        output_path=os.path.join(path["videos_final"], nome_arquivo)

        unir_cenas_com_transicoes(arquivos, transicoes, output_path)

        # 🔊 Etapa 2: Adicionar trilha sonora (com volume)
        if usar_trilha and trilha_file:
            trilha_path = os.path.join(path["videos_final"], secure_filename(trilha_file.filename))
            trilha_file.save(trilha_path)
            adicionar_trilha_sonora(output_path, trilha_path, output_path, volume)

        # 🖼️ Etapa 3: Adicionar marca d’água (com opacidade)
        if usar_marca and marca_file:
            marca_path = os.path.join(path["videos_final"], secure_filename(marca_file.filename))
            marca_file.save(marca_path)
            adicionar_marca_dagua(output_path, marca_path, output_path, opacidade)

        # 🧹 Etapa 4: Limpar temporários (_step_X.mp4)
        for f in os.listdir(path["videos_final"]):
            if "_step_" in f and f.endswith(".mp4"):
                os.remove(os.path.join(path["videos_final"], f))

        return jsonify({
            "status": "ok",
            "output": output_path,
            "nome_arquivo": nome_arquivo
        })

    except Exception as e:
        print("❌ Erro ao finalizar vídeo:", e)
        return jsonify({
            "status": "ok",
            "output": output_path,
            "nome_arquivo": nome_arquivo
        })


@app.route("/preview_audio_trilha", methods=["POST"])
def preview_audio_trilha():

    try:
        from flask import send_file
        trilha_file = request.files.get("trilha")
        volume_pct = int(request.form.get("volume", 25))
        volume = max(0.0, min(volume_pct / 100.0, 1.0))

        base = get_config("pasta_salvar") or os.getcwd()
        audio1_path = os.path.abspath(os.path.join(path["audios"], "narracao1.mp3"))
        if not trilha_file or not os.path.exists(audio1_path):
            return "Arquivo ausente", 400

        trilha_temp = os.path.abspath(os.path.join(path["base"], "trilha_temp.mp3"))
        trilha_file.save(trilha_temp)
        output = os.path.abspath(os.path.join(path["base"], "preview_mix.m4a"))

        subprocess.run([
            "ffmpeg", "-y",
            "-i", audio1_path,
            "-i", trilha_temp,
            "-filter_complex",
            f"[1:a]volume={volume}[trilha];[0:a][trilha]amix=inputs=2:duration=first[a]",
            "-map", "[a]", "-c:a", "aac", "-b:a", "192k", output
        ], check=True)

        return send_file(output, mimetype="audio/mp4")

    except Exception as e:
        print("❌ Erro no preview:", e)
        return "Erro ao gerar preview", 500


@app.route('/preview_video/<int:idx>')
def preview_video(idx):
    #base      = get_config("pasta_salvar") or "default"
    video_path = os.path.join(path["base"], "videos_cenas", f"video{idx+1}.mp4")
    if not os.path.isfile(video_path):
        return "Vídeo não encontrado", 404
    return send_file(video_path, mimetype='video/mp4')

@app.route('/modules/videos_cenas/<path:filename>')
def serve_videos_cenas(filename):
    return send_from_directory(
        os.path.join(app.root_path, 'modules', 'videos_cenas'),
        filename
    )

@app.route("/video_final/<nome>")
def servir_video_final(nome):
    from flask import send_from_directory
    return send_from_directory(path["videos_final"], nome)

@app.route("/cenas/excluir", methods=["POST"])
def cenas_excluir():
    data = request.get_json(silent=True) or {}
    idx0 = int(data.get("index0", -1))
    paths = get_paths()
    import shutil

    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    if not (0 <= idx0 < len(cenas)):
        return jsonify({"status":"erro","msg":"index fora do range"}), 400

    # Remove arquivos físicos da cena idx0 (imagem, áudio, srt, ass, vídeo)
    i1 = idx0 + 1
    def rm(p):
        try:
            if os.path.isfile(p): os.remove(p)
        except: pass

    for ext in (".jpg",".jpeg",".png",".mp4"):
        rm(os.path.join(paths["imagens"], f"imagem{i1}{ext}"))
    rm(os.path.join(paths["audios"], f"narracao{i1}.mp3"))
    rm(os.path.join(paths["legendas_srt"], f"legenda{i1}.srt"))
    rm(os.path.join(paths["legendas_ass"], f"legenda{i1}.ass"))
    rm(os.path.join(paths["videos_cenas"], f"video{i1}.mp4"))

    # Remove do JSON
    del cenas[idx0]

    # Persiste provisoriamente
    with open(paths["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    # Renumera tudo chamando reordenar com ordem identidade (0..n-1)
    # Isso força os arquivos remanescentes a assumirem a sequência nova
    ordem = list(range(len(cenas)))
    # Reaproveita sua lógica /cenas/reordenar chamando internamente:
    # (Opcional: você pode consolidar esse código com a função existente)
    return jsonify({"status":"ok"})

@app.route("/cenas/duplicar", methods=["POST"])
def cenas_duplicar():
    data = request.get_json(silent=True) or {}
    idx0 = int(data.get("index0", -1))
    paths = get_paths()
    import shutil

    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    if not (0 <= idx0 < len(cenas)):
        return jsonify({"status":"erro","msg":"index fora do range"}), 400

    nova = json.loads(json.dumps(cenas[idx0]))  # deep copy
    cenas.insert(idx0+1, nova)

    # Persiste JSON
    with open(paths["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    # Arquivos: copie se existirem (imagem, áudio, srt/ass, vídeo)
    src_i1 = idx0+1
    dst_i1 = idx0+2
    def copiar(src, dst):
        try:
          if os.path.isfile(src):
            shutil.copy2(src, dst)
        except: pass

    # descobrir ext da imagem
    img_ext = None
    for ext in (".jpg",".jpeg",".png",".mp4"):
        p = os.path.join(paths["imagens"], f"imagem{src_i1}{ext}")
        if os.path.exists(p):
            img_ext = ext; break
    if img_ext:
      copiar(os.path.join(paths["imagens"], f"imagem{src_i1}{img_ext}"),
             os.path.join(paths["imagens"], f"imagem{dst_i1}{img_ext}"))

    copiar(os.path.join(paths["audios"], f"narracao{src_i1}.mp3"),
           os.path.join(paths["audios"], f"narracao{dst_i1}.mp3"))
    copiar(os.path.join(paths["legendas_srt"], f"legenda{src_i1}.srt"),
           os.path.join(paths["legendas_srt"], f"legenda{dst_i1}.srt"))
    copiar(os.path.join(paths["legendas_ass"], f"legenda{src_i1}.ass"),
           os.path.join(paths["legendas_ass"], f"legenda{dst_i1}.ass"))
    copiar(os.path.join(paths["videos_cenas"], f"video{src_i1}.mp4"),
           os.path.join(paths["videos_cenas"], f"video{dst_i1}.mp4"))

    return jsonify({"status":"ok"})


#--------------------------------------------------------------------------------------------------------------------

# ========================== PREVIEW PROXY (360p) ==========================
def _ffprobe_streams(p):
    """Retorna dict {'v_dur': float, 'a_dur': float, 'has_audio': bool} para o arquivo p."""
    try:
        # Tenta pegar duração de vídeo (stream) e form.duration como fallback
        cmd = [
            "ffprobe","-v","error","-show_entries","stream=codec_type,duration",
            "-show_format","-of","json", p
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        j = json.loads(out)
        v_dur = None; a_dur = None; has_audio = False
        for s in j.get("streams", []):
            if s.get("codec_type") == "video":
                v_dur = float(s.get("duration")) if s.get("duration") else v_dur
            if s.get("codec_type") == "audio":
                has_audio = True
                a_dur = float(s.get("duration")) if s.get("duration") else a_dur
        # fallback: format.duration
        if v_dur is None:
            fd = j.get("format", {}).get("duration")
            if fd is not None:
                v_dur = float(fd)
        return {
            "v_dur": float(v_dur) if v_dur is not None else 0.0,
            "a_dur": float(a_dur) if a_dur is not None else 0.0,
            "has_audio": bool(has_audio)
        }
    except Exception:
        return {"v_dur": 0.0, "a_dur": 0.0, "has_audio": False}


def _hash_payload(payload_bytes, trilha_bytes=None, marca_bytes=None):
    h = hashlib.sha1()
    h.update(payload_bytes)
    if trilha_bytes: h.update(trilha_bytes)
    if marca_bytes:  h.update(marca_bytes)
    return h.hexdigest()


@app.route("/cache/preview/<path:nome>")
def serve_preview_cache(nome):
    path_dict = get_paths()
    cache_dir = os.path.join(path_dict["base"], "cache_preview")
    return send_from_directory(cache_dir, nome, as_attachment=False)


@app.route("/preview_timeline", methods=["POST"])
def preview_timeline():
    """
    Gera um MP4 360p 'ultrafast' com as cenas e transições atuais.
    Body:
      - JSON direto (Content-Type: application/json)  OU
      - FormData com campo 'payload' (JSON) + arquivos opcionais 'trilha' e 'marca'
    Retorno: { ok: true, url: "/cache/preview/<hash>.mp4" }
    """
    try:
        path_dict = get_paths()
        base = path_dict["base"]
        videos_dir = path_dict["videos_cenas"]
        cache_dir  = os.path.join(base, "cache_preview")
        os.makedirs(cache_dir, exist_ok=True)

        # --------- Lê payload + arquivos opcionais ---------
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            trilha_file = None
            marca_file  = None
            trilha_bytes = None
            marca_bytes  = None
        else:
            payload_raw = request.form.get("payload", "{}")
            payload = json.loads(payload_raw)
            trilha_file = request.files.get("trilha")
            marca_file  = request.files.get("marca")
            trilha_bytes = trilha_file.read() if trilha_file else None
            marca_bytes  = marca_file.read() if marca_file else None
            # rebobina para permitir salvar depois
            if trilha_file: trilha_file.stream.seek(0)
            if marca_file:  marca_file.stream.seek(0)

        order  = payload.get("order") or []  # índices base-0
        scenes = payload.get("scenes") or []
        slots  = payload.get("slots")  or []
        trilha = payload.get("trilha") or {}
        marca  = payload.get("marca")  or {}

        if not order:
            return jsonify({"ok": False, "message": "Sem cenas na timeline."}), 400

        # --------- Monta lista de inputs (arquivos de cena) ---------
        input_files = []
        durations   = []
        has_audio   = []

        for idx0 in order:
            idx1 = int(idx0) + 1
            p = os.path.join(videos_dir, f"video{idx1}.mp4")
            if not os.path.isfile(p):
                return jsonify({"ok": False, "message": f"Cena {idx1} não encontrada ({p}). Gere as cenas antes."}), 400
            input_files.append(p)
            info = _ffprobe_streams(p)
            durations.append(max(0.01, info["v_dur"]))  # mínima pra evitar zero
            has_audio.append(bool(info["has_audio"]))

        n = len(input_files)

        # --------- Transições (tamanho n-1) ---------
        # Normaliza com defaults
        trans_types = []
        trans_durs  = []
        for i in range(n-1):
            tp=(slots[i].get("tipo") if i < len(slots) and isinstance(slots[i], dict) else "") or ""
            du=(slots[i].get("duracao") if i < len(slots) and isinstance(slots[i], dict) else None)
            try:
                du=float(du) if du is not None else 0.3
            except Exception:
                du=0.3

            # se não houver transição, duração = 0 (corte seco)
            if not tp or tp in ("none", "sem", "sem_transicao", "sem_transição"):
                du=0.0

            # limites só se houver transição > 0
            if du > 0:
                du=max(0.1, min(2.0, du))

            trans_types.append(tp)
            trans_durs.append(du)

        # --------- Hash / cache ---------
        # Use o JSON puro + (hash dos arquivos opcionais)
        payload_bytes = json.dumps({
            "order": order, "slots": list(zip(trans_types, trans_durs)),
            "trilha": {"enabled": bool(trilha.get("enabled")), "volume": trilha.get("volume", 25)},
            "marca":  {"enabled": bool(marca.get("enabled")),  "opacidade": marca.get("opacidade", 100)}
        }, sort_keys=True).encode("utf-8")

        trilha_bytes_for_hash = None
        marca_bytes_for_hash  = None
        if request.files:
            if trilha_file:
                trilha_bytes_for_hash = trilha_bytes or trilha_file.read()
                trilha_file.stream.seek(0)
            if marca_file:
                marca_bytes_for_hash = marca_bytes or marca_file.read()
                marca_file.stream.seek(0)

        h = _hash_payload(payload_bytes, trilha_bytes_for_hash, marca_bytes_for_hash)
        out_name = f"preview_{h}.mp4"
        out_path = os.path.join(cache_dir, out_name)

        if os.path.exists(out_path):
            return jsonify({"ok": True, "url": f"/cache/preview/{out_name}"})

        # --------- Prepara inputs extras (trilha/marca) ---------
        add_inputs = []
        map_indices = {}  # {'trilha': N, 'marca': M}
        tmp_to_cleanup = []

        if trilha.get("enabled") and request.files and trilha_file:
            tmpt = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(trilha_file.filename or "trilha")[1] or ".mp3")
            trilha_file.save(tmpt.name)
            tmp_to_cleanup.append(tmpt.name)
            map_indices["trilha"] = len(input_files) + len(add_inputs)
            add_inputs.append(tmpt.name)

        if marca.get("enabled") and request.files and marca_file:
            tmpm = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(marca_file.filename or "marca")[1] or ".png")
            marca_file.save(tmpm.name)
            tmp_to_cleanup.append(tmpm.name)
            map_indices["marca"] = len(input_files) + len(add_inputs)
            # usamos -loop 1 para imagem
            add_inputs.append(tmpm.name)

        # --------- Construção do filter_complex ---------
        f = []  # linhas do filtergraph
        vlabels = []
        alabels = []

        # pré-processamento (escala/format para vídeo; sample rate/canais para áudio)
        for i in range(n):
            f.append(f"[{i}:v]scale=-2:540,setsar=1[v{i}s]")
            vlabels.append(f"v{i}s")
            if has_audio[i]:
                f.append(f"[{i}:a]aformat=fltp:44100:stereo,aresample=async=1:first_pts=0[a{i}s]")
            else:
                # áudio silencioso com duração do vídeo
                dur = durations[i]
                f.append(f"anullsrc=channel_layout=stereo:sample_rate=44100,atrim=duration={dur:.3f},asetpts=N/SR/TB[a{i}s]")
            alabels.append(f"a{i}s")

        # Corrente de xfade (vídeo) e acrossfade (áudio)
        if n == 1:
            last_v = vlabels[0]
            last_a = alabels[0]
        else:
            # offsets acumulados para xfade
            offsets = []
            cum = durations[0]
            for k in range(n-1):
                tk = trans_durs[k]
                offsets.append(max(0.0, cum - tk))
                cum = cum + durations[k+1] - tk

            last_v = vlabels[0]
            last_a = alabels[0]
            for k in range(1, n):
                trans=trans_types[k - 1]
                tdur=trans_durs[k - 1]
                off=offsets[k - 1]

                if trans and tdur > 0:
                    # há transição: usa xfade/acrossfade
                    f.append(
                        f"[{last_v}][{vlabels[k]}]xfade=transition={trans}:duration={tdur:.3f}:offset={off:.3f}[vx{k}]")
                    last_v=f"vx{k}"
                    f.append(f"[{last_a}][{alabels[k]}]acrossfade=d={tdur:.3f}:c1=tri:c2=tri[ax{k}]")
                    last_a=f"ax{k}"
                else:
                    # sem transição: corte seco com concat
                    f.append(f"[{last_v}][{vlabels[k]}]concat=n=2:v=1:a=0[vx{k}]")
                    last_v=f"vx{k}"
                    f.append(f"[{last_a}][{alabels[k]}]concat=n=2:v=0:a=1[ax{k}]")
                    last_a=f"ax{k}"

        # Marca d'água (opcional)
        if "marca" in map_indices:
            mi = map_indices["marca"]
            op = float(marca.get("opacidade", 100)) / 100.0
            op = max(0.0, min(1.0, op))
            f.append(f"[{mi}:v]format=rgba,colorchannelmixer=aa={op:.2f}[wm]")
            f.append(f"[{last_v}][wm]overlay=W-w-16:16:format=auto[vout]")
            last_v = "vout"

        # Trilha (opcional)
        if "trilha" in map_indices:
            ti = map_indices["trilha"]
            vol = float(trilha.get("volume", 25)) / 100.0
            vol = max(0.0, min(1.0, vol))
            f.append(f"[{ti}:a]aformat=fltp:44100:stereo,volume={vol:.3f}[atrilha]")
            f.append(f"[{last_a}][atrilha]amix=inputs=2:duration=first:normalize=0[aout]")
            last_a = "aout"

        filter_complex = ";".join(f)

        # --------- Comanda o ffmpeg ---------
        cmd = ["ffmpeg", "-y"]
        # inputs das cenas
        for p in input_files:
            cmd += ["-i", p]
        # inputs extras
        # - marca d'água como imagem: vamos usar -loop 1 para que dure to do o vídeo
        if "trilha" in map_indices:
            cmd += ["-i", add_inputs[ list(map_indices.keys()).index("trilha") ]]
        if "marca" in map_indices:
            # garante -loop 1 para a imagem (repetição)
            cmd += ["-loop", "1", "-i", add_inputs[ list(map_indices.keys()).index("marca") ]]

        cmd += [
            "-filter_complex", filter_complex,
            "-map", f"[{last_v}]",
            "-map", f"[{last_a}]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-g", "48", "-keyint_min", "48",
            "-movflags", "+faststart+frag_keyframe+empty_moov",
            out_path
        ]

        # Executa
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        finally:
            # limpa temporários
            for t in tmp_to_cleanup:
                try: os.remove(t)
                except Exception: pass

        return jsonify({"ok": True, "url": f"/cache/preview/{out_name}"})

    except subprocess.CalledProcessError as e:
        return jsonify({"ok": False, "message": e.stderr.decode('utf-8', 'ignore') if e.stderr else str(e)}), 500
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500
# ======================== /PREVIEW PROXY (360p) ============================



#----- CONFIGURAÇÕES ------------------------------------------------------------------------------------------------

@app.route("/configuracoes")
def pagina_configuracoes():
    """Exibe a tela de configurações do usuário."""
    return render_template("configuracoes.html", page_title="Configurações")

# caminho para o JSON gerado em etapas anteriores
def caminho_cenas_final():
    return path["cenas"]

def salvar_arquivo_upload(request_file, destino):
    if request_file:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        request_file.save(destino)
        return destino
    return None

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
    """Persiste as configurações enviadas pelo frontend e garante subpastas e arquivos base."""
    dados = request.get_json()

    try:
        # Salva a configuração criptografada
        salvar_config(dados)
        app.config['USUARIO_CONFIG'] = dados  # Atualiza config em tempo real
        print("🔐 Configurações gravadas com sucesso.")

        # Verifica se foi fornecido o caminho da pasta de salvamento
        pasta_salvar = dados.get("pasta_salvar")
        if pasta_salvar:
            # Garante subpastas de trabalho
            subpastas = [
                "imagens",
                "audios_narracoes",
                "legendas_ass",
                "legendas_srt",
                "videos_cenas",
                "videos_final"
            ]
            for nome in subpastas:
                caminho = os.path.join(pasta_salvar, nome)
                os.makedirs(caminho, exist_ok=True)
            print("📁 Subpastas criadas/verificadas.")

            # Agora garantimos os arquivos JSON iniciais
            from modules.paths import get_paths
            import json

            paths = get_paths()

            os.makedirs(os.path.dirname(paths["cenas"]), exist_ok=True)
            #os.makedirs(os.path.dirname(paths["cenas_com_imagens"]), exist_ok=True)

            if not os.path.exists(paths["cenas"]):
                with open(paths["cenas"], "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                print("📝 cenas.json criado.")

            # if not os.path.exists(paths["cenas_com_imagens"]):
            #     with open(paths["cenas_com_imagens"], "w", encoding="utf-8") as f:
            #         json.dump([], f, ensure_ascii=False, indent=2)
            #     print("📝 cenas_com_imagens.json criado.")

            # Opcional: criar ultimo_nome_video.txt com valor inicial
            if not os.path.exists(paths["nome_video"]):
                with open(paths["nome_video"], "w", encoding="utf-8") as f:
                    f.write("video1")
                print("🆕 ultimo_nome_video.txt criado com valor 'video1'.")

        else:
            print("⚠️ Nenhum caminho de pasta_salvar fornecido.")

        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ Erro ao salvar configurações:", e)
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

@app.before_request
def checar_configuracao():
    caminho = request.path

    # Lista de rotas que não precisam da config (evita loop)
    rotas_livres = ["/api/configuracoes", "/selecionar_pasta", "/configuracoes", "/salvar_config", "/static/", "/favicon.ico"]

    # Permitir se a rota está liberada
    if any(caminho.startswith(r) for r in rotas_livres):
        return

    # Verifica se a pasta de salvamento foi configurada
    pasta = get_config("pasta_salvar")

    if not pasta or not os.path.exists(pasta):
        print("🔒 Redirecionando: configuração não encontrada ou pasta inválida")
        return redirect(url_for("pagina_configuracoes"))  # Use o nome correto da view

from flask import request, jsonify
from modules.licenca import carregar_config_licenciada, salvar_config_licenciada, carregar_fernet
import json

from flask import request, jsonify
from modules.licenca import (
    carregar_config_licenciada,
    salvar_config_licenciada,
    carregar_fernet,
    get_hardware_id
)
import json

@app.route("/upload_config_licenciada", methods=["POST"])
def upload_config_licenciada():
    # Mantemos apenas para instalar config inicial; não permite recarga de créditos.
    if "arquivo" not in request.files:
        return jsonify({"status": "erro", "mensagem": "Arquivo ausente."}), 400

    arquivo = request.files["arquivo"]
    if not arquivo.filename.endswith(".json") and not arquivo.filename.endswith(".txt"):
        return jsonify({"status": "erro", "mensagem": "Formato inválido."}), 400

    try:
        conteudo = arquivo.read()
        fernet = carregar_fernet()
        dados = fernet.decrypt(conteudo).decode()
        novo_config = json.loads(dados)
    except Exception as e:
        return jsonify({"status":"erro","mensagem":"Arquivo inválido ou corrompido."}), 400

    # Se já existe configuração local, recusamos (evita soma indevida)
    if os.path.exists(os.path.join("configuracoes", "config_licenciado.json")):
        return jsonify({"status":"erro","mensagem":"Já existe configuração local. Use o pacote de crédito (.crd) para recarga."}), 400

    # Caso não exista, aceitar como instalação inicial (cria arquivo cifrado)
    try:
        os.makedirs("configuracoes", exist_ok=True)
        with open(os.path.join("configuracoes", "config_licenciado.json"), "wb") as f:
            f.write(conteudo)
        # opcional: persistir também o estado formal via salvar_estado_creditos
        try:
            estado = {
                "hardware_id": novo_config.get("hardware_id"),
                "creditos": int(novo_config.get("creditos", 0)),
                "api_key": novo_config.get("api_key", ""),
                "redeemed_ids": novo_config.get("redeemed_ids", []),
                "last_serial": int(novo_config.get("last_serial", 0) or 0)
            }
            salvar_estado_creditos(estado)
        except Exception:
            pass
        return jsonify({"status":"ok","mensagem":"Configuração instalada."})
    except Exception as e:
        return jsonify({"status":"erro","mensagem":str(e)}), 500


@app.route("/upload_credit_pack", methods=["POST"])
def upload_credit_pack():
    if "arquivo" not in request.files:
        return jsonify({"status":"erro","mensagem":"Arquivo ausente."}), 400

    arquivo = request.files["arquivo"]
    if not arquivo.filename.endswith(".crd"):
        return jsonify({"status":"erro","mensagem":"Formato inválido. Envie .crd"}), 400

    try:
        blob = arquivo.read()
        fernet = carregar_fernet()
        # decifra o pacote
        container = json.loads(fernet.decrypt(blob).decode())
        payload = container.get("payload")
        signature_b64 = container.get("signature")
        if not payload or not signature_b64:
            return jsonify({"status":"erro","mensagem":"Pacote inválido."}), 400

        signature = base64.b64decode(signature_b64)
        # verifica assinatura RSA
        pub = load_public_key()
        raw = json.dumps(payload, separators=(",",":")).encode()
        try:
            pub.verify(signature, raw, padding.PKCS1v15(), hashes.SHA256())
        except Exception:
            return jsonify({"status":"erro","mensagem":"Assinatura inválida."}), 400

        # valida hardware
        hw_local = get_hardware_id()
        if payload.get("hardware_id") != hw_local:
            return jsonify({"status":"erro","mensagem":"Pacote não pertence a este computador."}), 400

        # valida expiração (issued <= hoje <= expires)
        issued = datetime.fromisoformat(payload.get("issued"))
        expires = datetime.fromisoformat(payload.get("expires"))
        hoje = datetime.now()
        if hoje < issued or hoje > expires:
            return jsonify({"status":"erro","mensagem":"Pacote expirado."}), 400

        # anti-replay: credit_id e serial monotônico (usar maior entre estado e shadow)
        estado = ler_estado_creditos()
        redeemed = set(estado.get("redeemed_ids", []))
        last_serial_local = int(estado.get("last_serial", 0))
        last_serial_shadow = int(ler_shadow_serial() or 0)
        maior_serial = max(last_serial_local, last_serial_shadow)

        if payload.get("credit_id") in redeemed:
            return jsonify({"status":"erro","mensagem":"Este pacote já foi usado."}), 400

        if int(payload.get("serial", 0)) <= int(maior_serial):
            return jsonify({"status":"erro","mensagem":"Ordem inválida: serial não é maior que o último aplicado."}), 400

        # aplica crédito
        amount = int(payload.get("amount", 0))
        estado["creditos"] = int(estado.get("creditos", 0)) + amount
        redeemed.add(payload.get("credit_id"))
        estado["redeemed_ids"] = list(redeemed)
        estado["last_serial"] = int(payload.get("serial"))
        salvar_estado_creditos(estado)  # grava e atualiza shadow

        return jsonify({"status":"ok","mensagem":f"{amount} créditos adicionados."})

    except Exception as e:
        print("Erro ao processar pacote .crd:", e)
        return jsonify({"status":"erro","mensagem":"Pacote inválido ou corrompido."}), 400

@app.route("/cenas/reordenar", methods=["POST"])
def cenas_reordenar():
    """
    Reordena cenas e renomeia arquivos vinculados em duas fases (temp -> final),
    evitando colisões e deleções prematuras.
    Body JSON:
      - new_order: lista de índices base-0 com a NOVA ordem (p.ex. [3,0,1,2])
    """
    import uuid, shutil

    try:
        data = request.get_json(silent=True) or {}
        new_order = data.get("new_order")
        if not isinstance(new_order, list) or not all(isinstance(i, int) for i in new_order):
            return jsonify({"status": "erro", "msg": "new_order inválido"}), 400

        # Carrega cenas
        with open(path["cenas"], encoding="utf-8") as f:
            cenas = json.load(f)

        total = len(cenas)
        if sorted(new_order) != list(range(total)):
            return jsonify({"status": "erro", "msg": "new_order não corresponde aos índices existentes"}), 400

        # Mapa novo->antigo (novo 0 recebe o antigo X...)
        novo_para_antigo = {novo_idx: antigo_idx for novo_idx, antigo_idx in enumerate(new_order)}

        # Helpers
        def existe(p): return os.path.exists(p)
        def achar_ext_imagem(idx1):
            base = os.path.join(path["imagens"], f"imagem{idx1}")
            for ext in (".jpg", ".jpeg", ".png", ".mp4"):
                if existe(base + ext):
                    return ext
            return None

        # --- Colete TODOS os caminhos fonte existentes (por índice antigo) ---
        # Vamos criar dicionários { (tipo, antigo_idx1): src_path } SOMENTE para os que existem
        src_paths = {}  # chave: (tipo, antigo_idx1) -> caminho
        for antigo_idx in range(total):
            i1 = antigo_idx + 1

            # imagem (qualquer ext)
            img_ext = achar_ext_imagem(i1)
            if img_ext:
                src_paths[("img", i1)] = os.path.join(path["imagens"], f"imagem{i1}{img_ext}")

            # áudio
            p = os.path.join(path["audios"], f"narracao{i1}.mp3")
            if existe(p):
                src_paths[("aud", i1)] = p

            # srt
            p = os.path.join(path["legendas_srt"], f"legenda{i1}.srt")
            if existe(p):
                src_paths[("srt", i1)] = p

            # ass
            p = os.path.join(path["legendas_ass"], f"legenda{i1}.ass")
            if existe(p):
                src_paths[("ass", i1)] = p

            # video da cena
            p = os.path.join(path["videos_cenas"], f"video{i1}.mp4")
            if existe(p):
                src_paths[("vid", i1)] = p

        # --- FASE 1: mover TO DO mundo para nomes temporários únicos ---
        # Guardamos mapeamento temp->meta (tipo, antigo_idx1)
        temp_paths = {}  # temp_path -> (tipo, antigo_idx1)
        for key, src in src_paths.items():
            dirp = os.path.dirname(src)
            base = os.path.basename(src)
            tmp = os.path.join(dirp, f".reorder_tmp_{uuid.uuid4().hex}__{base}")
            os.replace(src, tmp)  # movimento atômico dentro do mesmo disco
            temp_paths[tmp] = key

        # --- FASE 2: mover de temporários para os destinos FINAIS (novo_idx) ---
        # Para cada novo_idx, descubra antigo_idx e crie destinos por tipo.
        for novo_idx, antigo_idx in novo_para_antigo.items():
            j1 = novo_idx + 1
            i1 = antigo_idx + 1

            # IMG
            key = ("img", i1)
            tmp = next((t for t, k in temp_paths.items() if k == key), None)
            if tmp:
                # precisamos inferir a extensão a partir do tmp (ou do i1 original)
                _, srcname = os.path.split(tmp)
                # srcname termina com algo tipo ...imagem{i1}.jpg
                _, ext = os.path.splitext(srcname)
                dst = os.path.join(path["imagens"], f"imagem{j1}{ext}")
                # se já existe dst, removemos (arquivo de destino antigo)
                if existe(dst):
                    os.remove(dst)
                os.replace(tmp, dst)

            # Áudio
            key = ("aud", i1)
            tmp = next((t for t, k in temp_paths.items() if k == key), None)
            if tmp:
                dst = os.path.join(path["audios"], f"narracao{j1}.mp3")
                if existe(dst):
                    os.remove(dst)
                os.replace(tmp, dst)

            # SRT
            key = ("srt", i1)
            tmp = next((t for t, k in temp_paths.items() if k == key), None)
            if tmp:
                dst = os.path.join(path["legendas_srt"], f"legenda{j1}.srt")
                if existe(dst):
                    os.remove(dst)
                os.replace(tmp, dst)

            # ASS
            key = ("ass", i1)
            tmp = next((t for t, k in temp_paths.items() if k == key), None)
            if tmp:
                dst = os.path.join(path["legendas_ass"], f"legenda{j1}.ass")
                if existe(dst):
                    os.remove(dst)
                os.replace(tmp, dst)

            # Vídeo
            key = ("vid", i1)
            tmp = next((t for t, k in temp_paths.items() if k == key), None)
            if tmp:
                dst = os.path.join(path["videos_cenas"], f"video{j1}.mp4")
                if existe(dst):
                    os.remove(dst)
                os.replace(tmp, dst)

        # --- Reordena o ARRAY de cenas conforme new_order ---
        cenas_nova = [cenas[i] for i in new_order]

        # --- Atualiza os campos de caminho de cada cena de acordo com o novo índice ---
        for novo_idx, cena in enumerate(cenas_nova):
            j1 = novo_idx + 1

            # áudio
            aud = os.path.join(path["audios"], f"narracao{j1}.mp3")
            cena["audio_path"] = aud if os.path.exists(aud) else None

            # srt
            srt = os.path.join(path["legendas_srt"], f"legenda{j1}.srt")
            cena["srt_path"] = srt if os.path.exists(srt) else None

            # ass
            ass = os.path.join(path["legendas_ass"], f"legenda{j1}.ass")
            cena["ass_path"] = ass if os.path.exists(ass) else None

            # imagem (descobrir extensão nova)
            img_ext = None
            for ext in (".jpg", ".jpeg", ".png", ".mp4"):
                if os.path.exists(os.path.join(path["imagens"], f"imagem{j1}{ext}")):
                    img_ext = ext
                    break

            if img_ext:
                arquivo_local = os.path.join(path["imagens"], f"imagem{j1}{img_ext}")
                cena["arquivo_local"] = arquivo_local
                # Se você tiver um endpoint de serve estável, prefira gerar a URL via frontend com url_for.
                # Aqui deixo só o caminho local; o template monta a URL com url_for('serve_module_images', filename=basename).
                cena["image_url"] = None
            else:
                cena["arquivo_local"] = None
                cena["image_url"] = None

        # Persiste
        with open(path["cenas"], "w", encoding="utf-8") as f:
            json.dump(cenas_nova, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok", "total": total})

    except Exception as e:
        print("❌ Erro em /cenas/reordenar:", e)
        return jsonify({"status": "erro", "msg": str(e)}), 500

@app.route("/cenas/resumo", methods=["GET"])
def cenas_resumo():
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    resumo = []
    for i, cena in enumerate(cenas, start=1):
        # Detecta mídia física:
        url = None
        tipo = None
        for ext, t in [(".jpg","image"), (".jpeg","image"), (".png","image"), (".mp4","video")]:
            p = os.path.join(path["imagens"], f"imagem{i}{ext}")
            if os.path.exists(p):
                url = f"/modules/imagens/imagem{i}{ext}"
                tipo = t
                break

        resumo.append({
            "index0": i-1,
            "numero": i,
            "prompt": cena.get("prompt_imagem", ""),
            "media_url": url,
            "media_tipo": tipo,
            "tem_media": bool(url)
        })
    return jsonify({"status": "ok", "cenas": resumo})
