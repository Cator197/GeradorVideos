"""Rotinas para juntar cenas individuais em um único vídeo final."""

import os
import json
import shutil
import zipfile
from moviepy import (
    VideoFileClip, concatenate_videoclips, AudioFileClip,
    CompositeVideoClip, ImageClip
)
from modules.config import get_config

# Caminhos principais
PASTA_BASE = get_config("pasta_salvar") or "default"
PASTA_VIDEOS = os.path.join(PASTA_BASE, "videos_cenas")
PASTA_SAIDA = os.path.join(PASTA_BASE, "videos_final")
PASTA_EXPORT = os.path.join(PASTA_BASE, "projeto_capcut")

os.makedirs(PASTA_SAIDA, exist_ok=True)


def obter_clips_de_video():
    """Retorna os caminhos ordenados dos vídeos da pasta de cenas."""
    arquivos = sorted([
        os.path.join(PASTA_VIDEOS, f)
        for f in os.listdir(PASTA_VIDEOS)
        if f.startswith("video") and f.endswith(".mp4")
    ])
    return arquivos


def aplicar_transicao(clips, tipo_transicao):
    """Aplica transição entre os clipes."""
    if not clips:
        raise ValueError("Nenhum vídeo encontrado para juntar.")

    if tipo_transicao == "crossfade":
        duracao = 0.5
        clips = [clips[0].fx(VideoFileClip.crossfadein, duracao)] + [
            c.crossfadein(duracao) for c in clips[1:]
        ]
        return concatenate_videoclips(clips, method="compose")

    elif tipo_transicao == "slide":
        return concatenate_videoclips(clips, method="compose", padding=-1, bg_color=(0, 0, 0))

    elif tipo_transicao in {"scroll", "freeze"}:
        return concatenate_videoclips(clips, method="compose")

    return concatenate_videoclips(clips, method="compose")  # Transição padrão


def aplicar_trilha_sonora(video, trilha_path, volume):
    """Adiciona uma trilha sonora ao vídeo final."""
    trilha = AudioFileClip(trilha_path).volumex(volume)
    return video.set_audio(trilha)


def aplicar_marca_dagua(video, marca_path, opacidade, posicao):
    """Sobrepõe uma imagem de marca d'água ao vídeo."""
    marca = (
        ImageClip(marca_path)
        .with_duration(video.duration)
        .resized(height=100)
        .with_opacity(opacidade)
        .with_position(eval(posicao))
    )
    return CompositeVideoClip([video, marca])


def run_juntar_cenas(
    tipo_transicao="cut",
    usar_musica=False,
    trilha_path=None,
    volume=0.2,
    usar_watermark=False,
    marca_path=None,
    opacidade=0.3,
    posicao="('right','bottom')"
):
    """Une as cenas individuais e aplica efeitos opcionais."""
    logs = []

    try:
        arquivos = obter_clips_de_video()
        if not arquivos:
            return {"logs": ["❌ Nenhuma cena encontrada na pasta 'videos_cenas'"]}

        clips = [VideoFileClip(f) for f in arquivos]

        video_final = aplicar_transicao(clips, tipo_transicao)
        logs.append(f"🎞️ {len(clips)} cenas unidas com transição: {tipo_transicao}")

        if usar_musica and trilha_path:
            video_final = aplicar_trilha_sonora(video_final, trilha_path, volume)
            logs.append("🎵 Trilha sonora aplicada")

        if usar_watermark and marca_path:
            video_final = aplicar_marca_dagua(video_final, marca_path, opacidade, posicao)
            logs.append("🌊 Marca d'água aplicada")

        saida = os.path.join(PASTA_SAIDA, "video_final.mp4")
        video_final.write_videofile(saida, fps=24, codec="libx264", audio_codec="aac", logger=None)
        logs.append(f"✅ Vídeo final salvo em {saida}")

        return {"logs": logs}

    except Exception as e:
        return {"logs": [f"❌ Erro ao gerar vídeo final: {str(e)}"]}


def exportar_para_capcut(trilha_path=None, marca_path=None):
    """Gera um pacote de projeto compatível com o CapCut."""
    logs = []

    try:
        videos = sorted([
            f for f in os.listdir(PASTA_VIDEOS)
            if f.startswith("video") and f.endswith(".mp4")
        ])

        if not videos:
            return {"logs": ["❌ Nenhuma cena disponível para exportação."]}

        # Recria estrutura do projeto
        if os.path.exists(PASTA_EXPORT):
            shutil.rmtree(PASTA_EXPORT)
        os.makedirs(os.path.join(PASTA_EXPORT, "videos"), exist_ok=True)

        # Copia cada vídeo da cena para a estrutura do projeto
        for video in videos:
            shutil.copy(
                os.path.join(PASTA_VIDEOS, video),
                os.path.join(PASTA_EXPORT, "videos", video)
            )
        logs.append(f"🎞️ {len(videos)} vídeos copiados")

        if trilha_path:
            shutil.copy(trilha_path, os.path.join(PASTA_EXPORT, "audio.mp3"))
            logs.append("🎵 Trilha sonora incluída")

        if marca_path:
            shutil.copy(marca_path, os.path.join(PASTA_EXPORT, "overlay.png"))
            logs.append("🌊 Marca d'água incluída")

        metadata = {
            "transicao": "manual",
            "clips": videos,
            "trilha": bool(trilha_path),
            "marca": bool(marca_path)
        }

        with open(os.path.join(PASTA_EXPORT, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logs.append("📄 Arquivo de metadados criado")

        # Compacta para ZIP
        zip_path = os.path.join(PASTA_SAIDA, "projeto_capcut.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(PASTA_EXPORT):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, PASTA_EXPORT)
                    zipf.write(full_path, rel_path)

        logs.append(f"✅ Projeto CapCut exportado: {zip_path}")
        return {"logs": logs, "arquivo": zip_path}

    except Exception as e:
        return {"logs": [f"❌ Erro ao exportar projeto: {str(e)}"]}
