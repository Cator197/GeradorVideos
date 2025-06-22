"""Montagem individual de cenas combinando imagem, áudio e legenda .ASS."""

import os
import json, sys
import subprocess
from moviepy import ImageClip, AudioFileClip
from modules.config import get_config
import shlex

# Caminhos principais
PASTA_BASE      = get_config("pasta_salvar") or os.getcwd()
ARQ_CENAS       = os.path.join(PASTA_BASE, "cenas_com_imagens.json")
PASTA_IMAGENS   = os.path.join(PASTA_BASE, "imagens")
PASTA_AUDIOS    = os.path.join(PASTA_BASE, "audios_narracoes")
PASTA_ASS       = os.path.join(PASTA_BASE, "legendas_ass")
PASTA_VIDEOS    = os.path.join(PASTA_BASE, "videos_cenas")

os.makedirs(PASTA_VIDEOS, exist_ok=True)

def criar_video_basico(imagem_path: str, audio_path: str, duracao: float, saida_path: str):
    """Cria um vídeo simples com imagem estática e áudio."""
    imagem_clip = ImageClip(imagem_path, duration=duracao).resized(height=1920)
    audio_clip = AudioFileClip(audio_path)
    video = imagem_clip.with_audio(audio_clip)
    video.write_videofile(saida_path, fps=24, logger=None)


def embutir_legenda_ass_ffmpeg(video_entrada, legenda_ass, video_saida):
    # Corrigir e escapar caminho da legenda
    vei = os.path.abspath(video_entrada)
    leg = os.path.abspath(legenda_ass)
    out = os.path.abspath(video_saida)

    # Escapando para o formato: C\:\\pasta\\arquivo.ass
    leg = leg.replace("\\", "\\\\").replace(":", "\\:")

    # Monta filtro com aspas simples internas
    filtro = f"subtitles='{leg}'"

    # Monta comando com filtro entre aspas duplas (por conta do shell do Windows)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "info", "-y",
        "-i", vei,
        "-vf", filtro,
        "-c:a", "copy",
        out
    ]

    print("DEBUG comando ffmpeg:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def run_montar_cenas(indices: list) -> dict:
    """Executa a montagem dos vídeos com legenda .ASS embutida."""
    logs = []

    with open(ARQ_CENAS, encoding="utf-8") as f:
        cenas = json.load(f)

    for i in indices:
        img_path = os.path.join(PASTA_IMAGENS, f"imagem{i+1}.jpg")
        aud_path = os.path.join(PASTA_AUDIOS, f"narracao{i+1}.mp3")
        ass_path = os.path.join(PASTA_ASS, f"legenda{i+1}.ass")
        temp_video = os.path.join(PASTA_VIDEOS, f"temp_video{i+1}.mp4")
        final_video = os.path.join(PASTA_VIDEOS, f"video{i+1}.mp4")

        if not (os.path.exists(img_path) and os.path.exists(aud_path) and os.path.exists(ass_path)):
            logs.append(f"⚠️ Arquivos faltando para a cena {i+1}")
            continue

        duracao = AudioFileClip(aud_path).duration
        logs.append(f"🎬 Criando vídeo base da cena {i+1}")
        criar_video_basico(img_path, aud_path, duracao, temp_video)

        logs.append(f"💬 Embutindo legenda ASS na cena {i+1}")
        embutir_legenda_ass_ffmpeg(temp_video, ass_path, final_video)
        os.remove(temp_video)
        logs.append(f"✅ Cena {i+1} gerada com legenda estilizada")

    return {"logs": logs}
