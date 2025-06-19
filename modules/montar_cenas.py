import os
import json
import re
import subprocess
from moviepy import ImageClip, AudioFileClip
from modules.config import get_config

# Caminhos principais
PASTA_BASE      = get_config("pasta_salvar") or os.getcwd()
ARQ_CENAS       = os.path.join(PASTA_BASE, "cenas_com_imagens.json")
PASTA_IMAGENS   = os.path.join(PASTA_BASE, "imagens")
PASTA_AUDIOS    = os.path.join(PASTA_BASE, "audios_narracoes")
PASTA_SRTS      = os.path.join(PASTA_BASE, "legendas_srt")
PASTA_VIDEOS    = os.path.join(PASTA_BASE, "videos_cenas")

os.makedirs(PASTA_VIDEOS, exist_ok=True)

def criar_video_basico(imagem_path: str, audio_path: str, duracao: float, saida_path: str):
    """Cria um vídeo simples com imagem estática e áudio."""
    imagem_clip = ImageClip(imagem_path, duration=duracao).resized(height=1920)
    audio_clip = AudioFileClip(audio_path)
    video = imagem_clip.with_audio(audio_clip)
    video.write_videofile(saida_path, fps=24, logger=None)

def embutir_legenda_ffmpeg(video_entrada: str, legenda_srt: str, video_saida: str,
                           cor: str = "white", tamanho: int = 24, posicao: str = "bottom"):
    """Embuti legenda no vídeo utilizando FFmpeg."""
    path_legenda = os.path.abspath(legenda_srt).replace("\\", "/")
    path_legenda = re.sub(r'^([A-Za-z]):', r'\1\\:', path_legenda)

    # Obter altura do vídeo
    height = int(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=height", "-of", "csv=p=0",
        video_entrada
    ]).strip())

    # Configurações da legenda
    align_map = {"bottom": (2, 20), "top": (8, 0)}
    align, marginV = align_map.get(posicao, (10, 0))

    style = (
        f"Fontsize={tamanho},"
        f"PrimaryColour=&Hffffff&,OutlineColour=&H000000&,"
        f"BorderStyle=1,Outline=1,Alignment={align},MarginV={marginV}"
    )
    filtro = f"subtitles='{path_legenda}':force_style='{style}'"

    comando = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", video_entrada, "-vf", filtro, "-c:a", "copy", video_saida
    ]
    subprocess.run(comando, check=True)

def run_montar_cenas(indices: list, usar_soft: bool, cor: str, tamanho: int, posicao: str) -> dict:
    """Executa a montagem dos vídeos com ou sem legendas embutidas."""
    logs = []

    with open(ARQ_CENAS, encoding="utf-8") as f:
        cenas = json.load(f)

    for i in indices:
        img_path = os.path.join(PASTA_IMAGENS, f"imagem{i+1}.jpg")
        aud_path = os.path.join(PASTA_AUDIOS, f"narracao{i+1}.mp3")
        srt_path = os.path.join(PASTA_SRTS, f"legenda{i+1}.srt")
        temp_video = os.path.join(PASTA_VIDEOS, f"temp_video{i+1}.mp4")
        final_video = os.path.join(PASTA_VIDEOS, f"video{i+1}.mp4")

        if not (os.path.exists(img_path) and os.path.exists(aud_path) and os.path.exists(srt_path)):
            logs.append(f"⚠️ Arquivos faltando para a cena {i+1}")
            continue

        duracao = AudioFileClip(aud_path).duration
        logs.append(f"🎬 Criando vídeo base da cena {i+1}")
        criar_video_basico(img_path, aud_path, duracao, temp_video)

        if usar_soft:
            os.replace(srt_path, os.path.join(PASTA_VIDEOS, f"video{i+1}.srt"))
            os.replace(temp_video, final_video)
            logs.append(f"✅ Cena {i+1} gerada (legenda soft)")
        else:
            logs.append(f"💬 Embutindo legenda hard na cena {i+1}")
            embutir_legenda_ffmpeg(temp_video, srt_path, final_video, cor, tamanho, posicao)
            os.remove(temp_video)
            logs.append(f"✅ Cena {i+1} gerada (legenda hard)")

    return {"logs": logs}
