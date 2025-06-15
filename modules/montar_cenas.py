import os
import json
import re
import subprocess
from moviepy import ImageClip, AudioFileClip
from modules.config import get_config

# Caminho base a partir da configuração do usuário
PASTA_BASE     = get_config("pasta_salvar") or os.getcwd()
ARQUIVO_CENAS = os.path.join(PASTA_BASE, "cenas_com_imagens.json")
PASTA_IMAGENS = os.path.join(PASTA_BASE, "imagens")
PASTA_AUDIOS  = os.path.join(PASTA_BASE, "audios_narracoes")
PASTA_SRTS    = os.path.join(PASTA_BASE, "legendas_srt")
PASTA_VIDEOS  = os.path.join(PASTA_BASE, "videos_cenas")

os.makedirs(PASTA_VIDEOS, exist_ok=True)

def criar_video_basico(imagem_path, audio_path, duracao, saida_path):
    clip_img   = ImageClip(imagem_path, duration=duracao)
    clip_audio = AudioFileClip(audio_path)
    clip_img = clip_img.resized(height=1920)  # proporção 9:16
    video = clip_img.with_audio(clip_audio)
    video.write_videofile(saida_path, fps=24, logger=None)

def embutir_legenda_ffmpeg(video_entrada, legenda_srt, video_saida, cor="white", tamanho=24, posicao="bottom"):
    legenda_path = os.path.abspath(legenda_srt).replace("\\", "/")
    legenda_path = re.sub(r'^([A-Za-z]):', r'\1\\:', legenda_path)
    height = int(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=height", "-of", "csv=p=0",
        video_entrada
    ]).strip())

    if posicao == "bottom": align, marginV = 2, 20
    elif posicao == "top": align, marginV = 8, 0
    else: align, marginV = 10, 0

    style = (
        f"Fontsize={tamanho},"
        f"PrimaryColour=&Hffffff&,OutlineColour=&H000000&,"
        f"BorderStyle=1,Outline=1,Alignment={align},MarginV={marginV}"
    )
    filtro = f"subtitles='{legenda_path}':force_style='{style}'"

    comando = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", video_entrada, "-vf", filtro, "-c:a", "copy", video_saida
    ]
    subprocess.run(comando, check=True)

def run_montar_cenas(indices, usar_soft, cor, tamanho, posicao):
    logs = []
    with open(ARQUIVO_CENAS, encoding="utf-8") as f:
        cenas = json.load(f)

    for i in indices:
        img  = os.path.join(PASTA_IMAGENS, f"imagem{i+1}.jpg")
        aud  = os.path.join(PASTA_AUDIOS,  f"narracao{i+1}.mp3")
        srt  = os.path.join(PASTA_SRTS,    f"legenda{i+1}.srt")
        temp = os.path.join(PASTA_VIDEOS,  f"temp_video{i+1}.mp4")
        out  = os.path.join(PASTA_VIDEOS,  f"video{i+1}.mp4")

        if not (os.path.exists(img) and os.path.exists(aud) and os.path.exists(srt)):
            logs.append(f"⚠️ Arquivos faltando p/ cena {i+1}")
            continue

        duracao = AudioFileClip(aud).duration
        logs.append(f"🎬 Criando vídeo base da cena {i+1}")
        criar_video_basico(img, aud, duracao, temp)

        if usar_soft:
            os.replace(srt, os.path.join(PASTA_VIDEOS, f"video{i+1}.srt"))
            os.replace(temp, out)
            logs.append(f"✅ Cena {i+1} gerada (legenda soft)")
        else:
            logs.append(f"💬 Embutindo legenda hard na cena {i+1}")
            embutir_legenda_ffmpeg(temp, srt, out, cor, tamanho, posicao)
            os.remove(temp)
            logs.append(f"✅ Cena {i+1} gerada (legenda hard)")

    return {"logs": logs}
