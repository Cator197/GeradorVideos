import os
import json
import re
import subprocess
from moviepy import ImageClip, AudioFileClip  # v2

# ——— Configurações de pastas ———
ARQUIVO_CENAS = "cenas_com_imagens.json"
PASTA_IMAGENS = "imagens"
PASTA_AUDIOS = "audios_narracoes"
PASTA_SRTS   = "legendas_srt"
PASTA_VIDEOS = "videos_cenas"
os.makedirs(PASTA_VIDEOS, exist_ok=True)

def criar_video_basico(imagem_path, audio_path, duracao, saida_path):
    clip_img   = ImageClip(imagem_path, duration=duracao)
    clip_audio = AudioFileClip(audio_path)
    video = clip_img.with_audio(clip_audio)
    video.write_videofile(saida_path, fps=24, logger=None)

def embutir_legenda_ffmpeg(video_entrada, legenda_srt, video_saida,
                           cor="white", tamanho=36, posicao="bottom"):
    # 1) gera o path absoluto com barras normais
    legenda_path = os.path.abspath(legenda_srt).replace("\\", "/")
    # 2) escapa o ':' do drive letter (ex: 'D:' → 'D\:')
    legenda_path = re.sub(r'^([A-Za-z]):', r'\1\\:', legenda_path)

    # 3) mapeia posição para ASS alignment
    align_map = {"bottom":2, "top":8, "center":5}
    align = align_map.get(posicao, 2)

    # 4) monta o filtro com o path entre aspas simples
    filtro = (
        f"subtitles='{legenda_path}':"
        f"force_style='Fontsize={tamanho},"
        f"PrimaryColour=&Hffffff&,OutlineColour=&H000000&,"
        f"BorderStyle=1,Outline=1,Alignment={align}'"
    )

    comando = [
        "ffmpeg", "-y",
        "-i", video_entrada,
        "-vf", filtro,
        "-c:a", "copy",
        video_saida
    ]
    subprocess.run(comando, check=True)

def processar_video(index, usar_soft, cor, tamanho, posicao):
    img  = os.path.join(PASTA_IMAGENS,  f"imagem{index+1}.jpg")
    aud  = os.path.join(PASTA_AUDIOS,  f"narracao{index+1}.mp3")
    srt  = os.path.join(PASTA_SRTS,    f"legenda{index+1}.srt")
    temp = os.path.join(PASTA_VIDEOS,  f"temp_video{index+1}.mp4")
    out  = os.path.join(PASTA_VIDEOS,  f"video{index+1}.mp4")

    if not (os.path.exists(img) and os.path.exists(aud) and os.path.exists(srt)):
        print(f"⚠️ Arquivos faltando p/ cena {index+1}")
        return

    duracao = AudioFileClip(aud).duration
    print(f"🎬 Cena {index+1}: criando vídeo base…")
    criar_video_basico(img, aud, duracao, temp)

    if usar_soft:
        os.replace(srt, os.path.join(PASTA_VIDEOS, f"video{index+1}.srt"))
        os.replace(temp, out)
        print(f"✅ Vídeo {out} (legenda soft) gerado")
    else:
        print(f"💬 Cena {index+1}: embutindo legenda hard…")
        embutir_legenda_ffmpeg(temp, srt, out, cor, tamanho, posicao)
        os.remove(temp)
        print(f"✅ Vídeo {out} (legenda hard) gerado")

if __name__ == "__main__":
    with open(ARQUIVO_CENAS, encoding="utf-8") as f:
        cenas = json.load(f)

    modo = input("🔹 Processar [T]odas as cenas ou [U]ma específica? (T/U): ").strip().lower()
    tipo = input("🔤 Legenda [H]ard (embutida) ou [S]oft (opcional)? (H/S): ").strip().lower()
    usar_soft = (tipo == "s")

    cor     = input("🎨 Cor do texto (ex: white, yellow): ").strip() or "white"
    tamanho = input("🔠 Tamanho da fonte (ex: 36): ").strip()
    tamanho = int(tamanho) if tamanho.isdigit() else 36
    posicao = input("📍 Posição [bottom, top, center]: ").strip().lower() or "bottom"

    if modo == "u":
        idx = int(input("Número da cena (1 para video1.mp4): ").strip()) - 1
        processar_video(idx, usar_soft, cor, tamanho, posicao)
    else:
        for i in range(len(cenas)):
            processar_video(i, usar_soft, cor, tamanho, posicao)
