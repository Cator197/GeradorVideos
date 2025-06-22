import os
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
    base = get_config("pasta_salvar") or os.getcwd()
    return {
        "audios": os.path.join(base, "audios_narracoes"),
        "legendas": os.path.join(base, "legendas_ass"),
    }

def fonte_instalada(fonte_nome):
    fontes = [os.path.basename(f.fname).split('.')[0].lower() for f in fm.fontManager.ttflist]
    return fonte_nome.lower() in fontes

def gerar_ass_com_whisper(modelo, path_audio, path_saida, estilo, modo="linha2"):
    segments, _ = modelo.transcribe(path_audio, word_timestamps=True)

    hex_color = estilo.get("cor", "#FFFFFF").lstrip("#")
    ass_cor = f"&H{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}FF"

    fonte = estilo.get("fonte", "Arial")
    if not fonte_instalada(fonte):
        print(f"[AVISO] Fonte '{fonte}' não instalada. Usando 'Arial'.")
        fonte = "Arial"

    tamanho = int(estilo.get("tamanho", 48))

    estilo_visual = estilo.get("estilo", "")
    animacao = estilo.get("animacao", "")

    override_visual = {
        "simples": "",
        "borda": r"{\bord2}",
        "sombra": r"{\shad3}",
        "glow": r"{\blur3}",
        "tv": r"{\fax0.2\shad2}",
        "retro": r"{\bord2\blur2\1c&H00FFFF&}",
        "cartoon": r"{\bord3\shad1}",
        "inverso": r"{\1c&H000000&\3c&HFFFFFF&}",
        "fundo": r"{\1a&H10&\3a&H80&}"
    }.get(estilo_visual, "")

    effect = ""
    override_anim = ""
    aplicar_k = animacao == "karaoke"

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

    nome_estilo = f"{fonte}_{tamanho}_{hex_color}_{estilo_visual}_{animacao}".replace(" ", "")

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
        f"Style: {nome_estilo},{fonte},{tamanho},{ass_cor},"
        "&H00FFDD00,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,5,10,10,960,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    agrupamento = {"palavra": 1, "linha1": 4, "linha2": 8, "linha3": 12}.get(modo, 8)
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
                    texto = "".join([f"{{\\k{duracao}}}{w.word}" for w in bloco])
                else:
                    texto = w.word if agrupamento == 1 else " ".join(w.word for w in bloco)
                linhas.append(f"Dialogue: 0,{inicio},{fim},{nome_estilo},,-1,,,{effect},{override_visual}{override_anim}{texto}")
                bloco = []

    if bloco:
        inicio = formatar_tempo(bloco[0].start)
        fim = formatar_tempo(bloco[-1].end)
        if aplicar_k:
            total_cs = int((bloco[-1].end - bloco[0].start) * 100)
            duracao = max(1, total_cs // len(bloco))
            texto = "".join([f"{{\\k{duracao}}}{w.word}" for w in bloco])
        else:
            texto = bloco[0].word if agrupamento == 1 else " ".join(w.word for w in bloco)
        linhas.append(f"Dialogue: 0,{inicio},{fim},{nome_estilo},,-1,,,{effect},{override_visual}{override_anim}{texto}")

    os.makedirs(os.path.dirname(path_saida), exist_ok=True)
    with open(path_saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
