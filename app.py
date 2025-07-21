"""Aplicação Flask para orquestrar as etapas de geração de vídeos."""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, send_file, Response, stream_with_context
import tkinter as tk
from tkinter import filedialog
from modules.config import salvar_config, carregar_config, get_config
from modules.parser_prompts import parse_prompts_txt, salvar_prompt_txt
from modules.gerar_imagens import run_gerar_imagens, calcular_indices, gerar_eventos_para_stream, gerar_imagens_async
from modules.gerar_narracao import iniciar_driver, login, gerar_e_baixar
from modules.gerar_ASS import gerar_ass_com_whisper, carregar_modelo
from modules.gerar_SRT import gerar_srt_com_bloco
from modules.paths import get_paths
import re, os, json, asyncio, time, subprocess, threading, sys
from modules.juntar_cenas import montar_uma_cena, adicionar_trilha_sonora, adicionar_marca_dagua, unir_cenas_com_transicoes
from modules.verify_license import verify_license
from werkzeug.utils import secure_filename
from modules.licenca import get_creditos


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

    #path = os.path.join(os.getcwd(),"cenas.json")
    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    #pasta_imagens = os.path.join(get_config("pasta_salvar"), "imagens")
    arquivos = os.listdir(path["imagens"])

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

    with open(path["cenas_com_imagens"], "w", encoding="utf-8") as f:
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

        with open(path["cenas_com_imagens"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)

        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"❌ Erro em upload_imagem: {e}")
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

@app.route("/legendas_srt", methods=["POST"])
def gerar_legendas_srt():
    data = request.get_json()
    scope = data.get("scope", "all")
    qtde_palavras = int(data.get("qtde_palavras", 4))

    single = data.get("single_index")
    start = data.get("from_index")

    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    if scope == "single" and single is not None:
        indices = [single]
    elif scope == "from" and start is not None:
        indices = list(range(start, len(cenas)))
    else:
        indices = list(range(1, len(cenas)))

    resultado = gerar_srt_com_bloco(indices, qtde_palavras)
    return jsonify({"status": "ok", "logs": resultado})

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
    with open(path["cenas_com_imagens"], encoding="utf-8") as f:
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
    with open(path["cenas_com_imagens"], encoding="utf-8") as f:
        cenas_existentes = json.load(f)

    for i, cena in enumerate(cenas_config):
        cenas_existentes[i].update(cena)

    with open(path["cenas_com_imagens"], "w", encoding="utf-8") as f:
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


#--------------------------------------------------------------------------------------------------------------------



#----- CONFIGURAÇÕES ------------------------------------------------------------------------------------------------

@app.route("/configuracoes")
def pagina_configuracoes():
    """Exibe a tela de configurações do usuário."""
    return render_template("configuracoes.html", page_title="Configurações")

# caminho para o JSON gerado em etapas anteriores
def caminho_cenas_final():
    return os.path.join(get_config("pasta_salvar") or ".", "cenas_com_imagens.json")

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
    """Persiste as configurações enviadas pelo frontend e garante subpastas."""
    dados = request.get_json()
    #print("📝 Config recebido do front-end:", dados)

    try:
        # Salva a configuração criptografada
        salvar_config(dados)
        app.config['USUARIO_CONFIG'] = dados  # Atualiza config em tempo real
        print("🔐 Gravado com sucesso.")

        # Verifica se foi fornecido o caminho da pasta de salvamento
        pasta_salvar = dados.get("pasta_salvar")
        if pasta_salvar:
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
            print("📁 Pastas de salvamento verificadas/criadas com sucesso.")
        else:
            print("⚠️ Nenhum caminho de pasta_salvar fornecido.")

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
    if "arquivo" not in request.files:
        return jsonify({"status": "erro", "mensagem": "Arquivo ausente."})

    arquivo = request.files["arquivo"]
    if not arquivo.filename.endswith(".json") and not arquivo.filename.endswith(".txt"):
        return jsonify({"status": "erro", "mensagem": "Formato inválido."})

    try:
        conteudo = arquivo.read()
        fernet = carregar_fernet()
        dados = fernet.decrypt(conteudo).decode()
        novo_config = json.loads(dados)

        # Carrega configuração atual
        atual = carregar_config_licenciada()

        # Verifica se pertence ao mesmo hardware
        if novo_config.get("hardware_id") != get_hardware_id():
            return jsonify({"status": "erro", "mensagem": "Arquivo não pertence a este computador."})

        # Soma os créditos
        creditos_novos = novo_config.get("creditos", 0)
        atual["creditos"] += creditos_novos

        # Atualiza api_key se presente
        if "api_key" in novo_config:
            atual["api_key"] = novo_config["api_key"]

        # Salva nova configuração
        salvar_config_licenciada(atual)

        return jsonify({"status": "ok", "mensagem": f"{creditos_novos} créditos adicionados com sucesso."})

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)})


