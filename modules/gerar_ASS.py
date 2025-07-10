import os
import ctypes
import shutil
import zipfile
import requests
from pathlib import Path
from faster_whisper import WhisperModel
from modules.config import get_config
import matplotlib.font_manager as fm

def carregar_modelo():
    return WhisperModel("small", device="cpu", compute_type="int8")

def formatar_tempo(segundos):
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    cs = int((segundos - int(segundos)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"

def get_paths():

    """Obtém os diretórios utilizados para salvar arquivos de áudio e cenas."""
    base = get_config("pasta_salvar") or os.getcwd()
    # Diretório da pasta modules (onde está este arquivo)
    BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ARQUIVO_JSON=os.path.join(BASE_DIR, "cenas.json")
    return {
        "audios": os.path.join(base, "audios_narracoes"),
        "legendas": os.path.join(base, "legendas_ass"),
        "cenas": os.path.join(os.getcwd(), "cenas.json"),
    }


import os
import re

def hex_ass(cor_hex: str) -> str:
    """
    Converte uma cor #RRGGBB para formato ASS: &HAABBGGRR
    Assume alpha 00 (sem transparência).
    """
    print(f"🎨 hex_ass recebida: {cor_hex}")

    if not cor_hex or not isinstance(cor_hex, str):
        print("⚠️ Cor inválida: tipo ou valor nulo. Usando fallback amarelo.")
        return "&H00FFFF00"

    cor_hex = cor_hex.strip().upper()

    if not cor_hex.startswith("#") or len(cor_hex) != 7:
        print("⚠️ Cor malformada (esperado #RRGGBB). Usando fallback amarelo.")
        return "&H00FFFF00"

    try:
        r = cor_hex[1:3]
        g = cor_hex[3:5]
        b = cor_hex[5:7]
        print(f"🧩 R: {r}, G: {g}, B: {b}")
        ass = f"&H00{b}{g}{r}"
        print(f"✅ Conversão ASS: {ass}")
        return ass
    except Exception as e:
        print(f"❌ Erro ao processar cor: {e}")
        return "&H00FFFF00"



def gerar_ass_com_whisper(modelo, path_audio, path_saida, estilo, modo="linha2"):
    segments, _ = modelo.transcribe(path_audio, word_timestamps=True)

    # Cores recebidas do frontend
    cor_primaria = hex_ass(estilo.get("cor_primaria", "#FFFF00"))
    print("cor primaria recebida do front: ", estilo.get("cor_primaria"))
    cor_secundaria = hex_ass(estilo.get("cor_secundaria", "#00FFFF"))  # Karaoke
    print("cor secundaria recebida do front: ", estilo.get("cor_secundaria"))
    cor_outline = hex_ass(estilo.get("cor_outline", "#000000"))
    cor_back = hex_ass(estilo.get("cor_back", "#000000"))

    # Cores para inline (sem &H)
    cor_primaria_inline = cor_primaria[2:]
    cor_secundaria_inline = cor_secundaria[2:]
    cor_outline_inline = cor_outline[2:]
    cor_back_inline = cor_back[2:]

    tamanho = int(estilo.get("tamanho", 48)) * 2
    estilo_visual = estilo.get("estilo", "simples").lower()
    animacao = estilo.get("animacao", "").lower()

    aplicar_k = animacao == "karaoke"
    palavra_acumulativa = animacao == "palavra acumulativa"

    # 🔧 Determina Outline e Shadow do estilo ASS (header)
    outline_val = 0
    shadow_val = 0
    if estilo_visual == "borda":
        outline_val = 2
    elif estilo_visual == "glow":
        outline_val = 5
    elif estilo_visual == "sombra":
        shadow_val = 3
    elif estilo_visual == "tv":
        shadow_val = 2
        outline_val = 1

    # 🎨 Override visual (ASS inline)
    tags = [f"\\1c{cor_primaria_inline}"]
    if estilo_visual in ("borda", "glow", "tv"):
        tags.append(f"\\3c{cor_outline_inline}")
    if estilo_visual == "sombra":
        tags.append(f"\\4c{cor_back_inline}")
    if estilo_visual == "borda":
        tags.append("\\bord2")
    elif estilo_visual == "glow":
        tags.append("\\blur3")
    elif estilo_visual == "sombra":
        tags.append("\\shad3")
    elif estilo_visual == "tv":
        tags.append("\\fax0.2\\shad2")

    override_visual = "{" + "".join(tags) + "}"

    # 🎞️ Animações
    override_anim = ""
    effect = ""
    if animacao == "fade":
        override_anim = r"{\alpha&HFF&\t(0,500,\alpha&H00&)}"
    elif animacao == "zoom":
        override_anim = r"{\t(0,500,\fscx120\fscy120)\t(500,1000,\fscx100\fscy100)}"
    elif animacao == "deslizar":
        override_anim = r"{\move(0,0,0,0)}"

    nome_estilo = f"Estilo_{estilo_visual}_{animacao}_{cor_primaria_inline[4:]}"

    # 📄 Cabeçalho ASS
    linhas = [
        "[Script Info]",
        "Title: Legendas Estilizadas",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic,"
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL,"
        "MarginR, MarginV, Encoding",
        f"Style: {nome_estilo},Arial,{tamanho},{cor_primaria},{cor_secundaria},{cor_outline},{cor_back},0,0,0,0,100,100,0,0,1,{outline_val},{shadow_val},5,10,10,150,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    # 🕒 Modo por palavra
    if modo == "palavra":
        for seg in segments:
            if not hasattr(seg, "words"):
                continue
            for word in seg.words:
                inicio = formatar_tempo(word.start)
                fim = formatar_tempo(word.end)
                texto = word.word.strip()
                if not texto:
                    continue

                if aplicar_k:
                    duracao = int((word.end - word.start) * 100)
                    legenda = f"{{\\1c{cor_primaria_inline}\\3c{cor_outline_inline}\\2c{cor_secundaria_inline}\\k{duracao}}}{texto}"
                else:
                    legenda = f"{override_visual}{override_anim}{texto}"

                linhas.append(f"Dialogue: 0,{inicio},{fim},{nome_estilo},,-1,,,{effect},{legenda}")


        os.makedirs(os.path.dirname(path_saida), exist_ok=True)
        with open(path_saida, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))
        return

    # 📚 Modo agrupado
    agrupamento = {"linha1": 4, "linha2": 8, "linha3": 12}.get(modo, 8)
    bloco = []

    for seg in segments:
        if not hasattr(seg, "words"):
            continue
        for word in seg.words:
            bloco.append(word)
            if len(bloco) >= agrupamento:
                inicio = formatar_tempo(bloco[0].start)
                fim = formatar_tempo(bloco[-1].end)

                if aplicar_k:
                    total_cs = int((bloco[-1].end - bloco[0].start) * 100)
                    duracao = max(1, total_cs // len(bloco))
                    texto = "".join([
                        f"{{\\1c{cor_primaria_inline}\\3c{cor_outline_inline}\\2c{cor_secundaria_inline}\\k{duracao}}}{w.word}"
                        for w in bloco
                    ])
                elif palavra_acumulativa:
                    acumulado = ""
                    for i in range(len(bloco)):
                        acumulado += bloco[i].word + " "
                        inicio_i = formatar_tempo(bloco[i].start)
                        fim_i = formatar_tempo(bloco[i].end)
                        linhas.append(
                            f"Dialogue: 0,{inicio_i},{fim_i},{nome_estilo},,-1,,,{effect},{override_visual}{override_anim}{acumulado.strip()}"
                        )
                    bloco = []
                    continue
                else:
                    texto = " ".join(w.word for w in bloco)

                linhas.append(
                    f"Dialogue: 0,{inicio},{fim},{nome_estilo},,-1,,,{effect},{override_visual}{override_anim}{texto}"
                )
                bloco = []

    # Último bloco
    if bloco and not palavra_acumulativa:
        inicio = formatar_tempo(bloco[0].start)
        fim = formatar_tempo(bloco[-1].end)
        if aplicar_k:
            total_cs = int((bloco[-1].end - bloco[0].start) * 100)
            duracao = max(1, total_cs // len(bloco))
            texto = "".join([
                f"{{\\1c{cor_primaria_inline}\\3c{cor_outline_inline}\\2c{cor_secundaria_inline}\\k{duracao}}}{w.word}"
                for w in bloco
            ])
        else:
            texto = " ".join(w.word for w in bloco)

        linhas.append(
            f"Dialogue: 0,{inicio},{fim},{nome_estilo},,-1,,,{effect},{override_visual}{override_anim}{texto}"
        )

    os.makedirs(os.path.dirname(path_saida), exist_ok=True)
    with open(path_saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

