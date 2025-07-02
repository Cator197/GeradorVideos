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
    BASE_DIR=os.path.dirname(os.path.abspath(__file__))
    ARQUIVO_JSON=os.path.join(BASE_DIR, "cenas.json")
    return {
        "audios": os.path.join(base, "audios_narracoes"),
        "legendas": os.path.join(base, "legendas_ass"),
        "cenas": os.path.join(BASE_DIR, "cenas.json"),
    }

def fonte_instalada(fonte_nome):
    fontes = [os.path.basename(f.fname).split('.')[0].lower() for f in fm.fontManager.ttflist]
    return fonte_nome.lower() in fontes

def instalar_fonte_ttf(path_ttf):
    pasta_fontes = os.path.join(os.environ['WINDIR'], 'Fonts')
    nome_arquivo = os.path.basename(path_ttf)
    destino = os.path.join(pasta_fontes, nome_arquivo)

    try:
        if not os.path.exists(destino):
            shutil.copy(path_ttf, destino)
            ctypes.windll.gdi32.AddFontResourceW(destino)
            print(f"✅ Fonte instalada: {nome_arquivo}")
        else:
            print(f"ℹ️ Fonte já está instalada: {nome_arquivo}")
        return True
    except Exception as e:
        print(f"❌ Erro ao instalar fonte: {e}")
        return False

def baixar_fonte_ttf_github(fonte_nome, variante="Regular"):
    pasta_fonts = os.path.join(os.path.dirname(__file__), "fonts")
    os.makedirs(pasta_fonts, exist_ok=True)

    nome_slug = fonte_nome.lower().replace(" ", "")
    nome_arquivo = f"{fonte_nome.replace(' ', '')}-{variante}.ttf"
    path_ttf = os.path.join(pasta_fonts, nome_arquivo)

    # Caminho com subpasta 'static' para fontes modernas como Montserrat
    url = f"https://github.com/google/fonts/raw/main/ofl/{nome_slug}/static/{nome_arquivo}"
    print(f"⬇️ Baixando fonte de: {url}")

    try:
        r = requests.get(url)
        if r.status_code == 200:
            with open(path_ttf, "wb") as f:
                f.write(r.content)
            print(f"✅ Fonte salva em: {path_ttf}")
            return instalar_fonte_ttf(path_ttf)
        else:
            print(f"❌ Erro ao baixar fonte: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Falha geral ao baixar fonte do GitHub: {e}")
        return False



def garantir_fonte_instalada(fonte_nome):
    if fonte_instalada(fonte_nome):
        return fonte_nome

    pasta_fonts = os.path.join(os.path.dirname(__file__), "fonts")
    candidatos = [f for f in os.listdir(pasta_fonts) if f.lower().endswith(".ttf") and fonte_nome.lower() in f.lower()]
    if candidatos:
        if instalar_fonte_ttf(os.path.join(pasta_fonts, candidatos[0])):
            return fonte_nome

    if baixar_fonte_ttf_github(fonte_nome):
        return fonte_nome

    print("⚠️ Fallback para Arial.")
    return "Arial"

import re

import os
import re

def hex_ass(cor_hex):
    """Converte #RRGGBB para &H00BBGGRR com alpha 00 (sem transparência)"""
    if isinstance(cor_hex, str) and re.match(r"^#[0-9A-Fa-f]{6}$", cor_hex.strip()):
        r, g, b = cor_hex[1:3], cor_hex[3:5], cor_hex[5:7]
        return f"&H00{b.upper()}{g.upper()}{r.upper()}"
    return "&H00FFFFFF"

def gerar_ass_com_whisper(modelo, path_audio, path_saida, estilo, modo="linha2"):
    from modules.gerar_ASS import garantir_fonte_instalada, formatar_tempo
    segments, _ = modelo.transcribe(path_audio, word_timestamps=True)

    ass_cor = hex_ass(estilo.get("cor", "#FFFF00"))
    ass_cor_inline = ass_cor[2:]

    ass_visual = hex_ass(estilo.get("cor_estilo_visual", "#000000"))
    ass_visual_inline = ass_visual[2:]

    ass_karaoke_inline = hex_ass(estilo.get("cor_karaoke", "#00FFFF"))[2:]

    fonte = garantir_fonte_instalada(estilo.get("fonte", "Arial"))
    tamanho = int(estilo.get("tamanho", 48)) * 2

    estilo_visual = estilo.get("estilo", "simples")
    animacao = estilo.get("animacao", "").lower()
    aplicar_k = animacao == "karaoke"
    palavra_acumulativa = animacao == "palavra acumulativa"

    override_visual = {
        "simples": f"{{\\1c{ass_cor_inline}\\3c{ass_cor_inline}}}",
        "borda": f"{{\\bord2\\1c{ass_cor_inline}\\3c{ass_visual_inline}}}",
        "sombra": f"{{\\shad3\\1c{ass_cor_inline}\\3c{ass_visual_inline}}}",
        "glow": f"{{\\blur3\\1c{ass_cor_inline}\\3c{ass_visual_inline}}}",
        "tv": f"{{\\fax0.2\\shad2\\1c{ass_cor_inline}\\3c{ass_visual_inline}}}",
        "retro": f"{{\\bord2\\blur2\\1c{ass_cor_inline}\\3c{ass_visual_inline}}}",
        "cartoon": f"{{\\bord3\\shad1\\1c{ass_cor_inline}\\3c{ass_visual_inline}}}",
        "inverso": f"{{\\1c&H000000&\\3c{ass_cor_inline}}}",
        "fundo": f"{{\\1c{ass_cor_inline}\\1a&H10&\\3a&H80&}}"
    }.get(estilo_visual, f"{{\\1c{ass_cor_inline}\\3c{ass_cor_inline}}}")

    override_anim = ""
    effect = ""
    if animacao == "fade":
        effect = "fade(0,255,0,500)"
    elif animacao == "zoom":
        override_anim = r"{\t(0,500,\fscx120\fscy120)\t(500,1000,\fscx100\fscy100)}"
    elif animacao == "piscar":
        override_anim = r"{\t(0,250,\alpha&HFF&)\t(250,500,\alpha&H00&)}"
    elif animacao == "pulsar":
        override_anim = r"{\t(0,500,\fs60)\t(500,1000,\fs48)}"
    elif animacao == "deslizar":
        effect = "move(0,720,0,650)"

    nome_estilo = f"{fonte}_{tamanho}_{ass_cor_inline[4:]}_{estilo_visual}_{animacao}".replace(" ", "")

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
        f"Style: {nome_estilo},{fonte},{tamanho},{ass_cor},&H00FFDD00,{ass_visual},&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,150,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    # Modo "por palavra"
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
                    legenda = f"{{\\1c{ass_cor_inline}\\3c{ass_cor_inline}\\2c{ass_karaoke_inline}&\\k{duracao}}}{texto}"
                else:
                    legenda = f"{override_visual}{override_anim}{texto}"

                linhas.append(
                    f"Dialogue: 0,{inicio},{fim},{nome_estilo},,-1,,,{effect},{legenda}"
                )
        os.makedirs(os.path.dirname(path_saida), exist_ok=True)
        with open(path_saida, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))
        return

    # Modo por linha (linha1, linha2, linha3, acumulativa)
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
                        f"{{\\1c{ass_cor_inline}\\3c{ass_cor_inline}\\2c{ass_karaoke_inline}&\\k{duracao}}}{w.word}"
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

    if bloco and not palavra_acumulativa:
        inicio = formatar_tempo(bloco[0].start)
        fim = formatar_tempo(bloco[-1].end)
        if aplicar_k:
            total_cs = int((bloco[-1].end - bloco[0].start) * 100)
            duracao = max(1, total_cs // len(bloco))
            texto = "".join([
                f"{{\\1c{ass_cor_inline}\\3c{ass_cor_inline}\\2c{ass_karaoke_inline}&\\k{duracao}}}{w.word}"
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

