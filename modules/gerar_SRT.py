import os
import json
from modules.config import get_config
from pydub import AudioSegment
from faster_whisper import WhisperModel

def get_paths():
    base = get_config("pasta_salvar") or os.getcwd()
    return {
        "base": base,
        "audios": os.path.join(base, "audios_narracoes"),
        "srts": os.path.join(base, "legendas_srt"),
        "cenas": os.path.join(base, "cenas_com_imagens.json"),
        "srt_geral": os.path.join(base, "legendas_srt", "legenda_completa.srt"),
    }

def formatar_tempo(segundos):
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos - int(segundos)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def carregar_modelo():
    return WhisperModel("small", device="cpu", compute_type="int8")

def gerar_srt_por_palavra(model, audio_path, srt_path):
    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    linhas = []
    contador = 1

    for seg in segments:
        for palavra in seg.words:
            ini = formatar_tempo(palavra.start)
            fim = formatar_tempo(palavra.end)
            texto = palavra.word.strip()
            linhas.append(f"{contador}\n{ini} --> {fim}\n{texto}\n")
            contador += 1

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

def gerar_srt_soft(indices):
    paths = get_paths()
    model = carregar_modelo()
    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    linhas = []
    contador = 1
    offset = 0.0

    for i in indices:
        audio = os.path.join(paths["audios"], f"narracao{i + 1}.mp3")
        if not os.path.exists(audio):
            continue

        segments, _ = model.transcribe(audio, word_timestamps=True)
        for seg in segments:
            for palavra in seg.words:
                ini = formatar_tempo(palavra.start + offset)
                fim = formatar_tempo(palavra.end + offset)
                texto = palavra.word.strip()
                linhas.append(f"{contador}\n{ini} --> {fim}\n{texto}\n")
                contador += 1

        offset += AudioSegment.from_file(audio).duration_seconds

    os.makedirs(paths["srts"], exist_ok=True)
    with open(paths["srt_geral"], "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

def run_gerar_legendas(indices, tipo="hard"):
    paths = get_paths()
    os.makedirs(paths["srts"], exist_ok=True)
    model = carregar_modelo()

    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    logs = []

    if tipo == "soft":
        gerar_srt_soft(indices)
        logs.append(f"Legenda geral salva em {paths['srt_geral']}")
        return {"logs": logs, "cenas": cenas}

    for i in indices:
        audio = os.path.join(paths["audios"], f"narracao{i + 1}.mp3")
        srt = os.path.join(paths["srts"], f"legenda{i + 1}.srt")

        if os.path.exists(audio):
            gerar_srt_por_palavra(model, audio, srt)
            cenas[i]["srt_path"] = srt
            logs.append(f"Legenda {i + 1} salva em {srt}")
        else:
            logs.append(f"Áudio {i + 1} não encontrado")

    with open(paths["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return {"logs": logs, "cenas": cenas}
