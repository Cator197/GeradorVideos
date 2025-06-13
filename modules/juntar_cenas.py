import os
import subprocess
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip, ImageClip

BASE_DIR = os.path.dirname(__file__)
PASTA_VIDEOS = os.path.join(BASE_DIR, "videos_cenas")
PASTA_SAIDA = os.path.join(BASE_DIR, "videos_final")
os.makedirs(PASTA_SAIDA, exist_ok=True)

def run_juntar_cenas(tipo_transicao, usar_musica, trilha_path, volume, usar_watermark, marca_path, opacidade, posicao):
    logs = []
    try:
        arquivos = sorted([
            os.path.join(PASTA_VIDEOS, f) for f in os.listdir(PASTA_VIDEOS)
            if f.startswith("video") and f.endswith(".mp4")
        ])

        if not arquivos:
            return {"logs": ["❌ Nenhuma cena encontrada em videos_cenas/"]}

        clips = [VideoFileClip(f) for f in arquivos]

        if tipo_transicao == "crossfade":
            duracao = 0.5
            clips[0] = clips[0].fx(VideoFileClip.crossfadein, duracao)
            final = clips[0]
            for c in clips[1:]:
                final = concatenate_videoclips([final, c.crossfadein(duracao)], method="compose")
        elif tipo_transicao == "slide":
            final = concatenate_videoclips(clips, method="compose", padding=-1, bg_color=(0,0,0))
        elif tipo_transicao == "scroll":
            final = concatenate_videoclips(clips, method="compose")
        elif tipo_transicao == "freeze":
            final = concatenate_videoclips(clips, method="compose")
        else:  # corte seco
            final = concatenate_videoclips(clips, method="compose")

        logs.append(f"🎞️ {len(clips)} cenas unidas com transição: {tipo_transicao}")

        if usar_musica and trilha_path:
            trilha = AudioFileClip(trilha_path).volumex(volume)
            final = final.set_audio(trilha)
            logs.append("🎵 Trilha sonora aplicada")

        if usar_watermark and marca_path:
            marca = (ImageClip(marca_path)
                     .with_duration(final.duration)
                     .resized(height=100)
                     .with_opacity(opacidade)
                     .with_pos(eval(posicao)))
            final = CompositeVideoClip([final, marca])
            logs.append("🌊 Marca d'água aplicada")

        saida = os.path.join(PASTA_SAIDA, "video_final.mp4")
        final.write_videofile(saida, fps=24, codec="libx264", audio_codec="aac", logger=None)
        logs.append(f"✅ Vídeo final salvo em {saida}")
        return {"logs": logs}
    except Exception as e:
        return {"logs": [f"❌ Erro: {str(e)}"]}


import os
import json
import shutil
import zipfile

def exportar_para_capcut(trilha_path=None, marca_path=None):
    logs = []
    try:
        base_dir = os.path.join("modules", "videos_cenas")
        temp_dir = os.path.join("modules", "projeto_capcut")
        videos = sorted([f for f in os.listdir(base_dir) if f.startswith("video") and f.endswith(".mp4")])

        if not videos:
            return {"logs": ["❌ Nenhuma cena disponível para exportação."]}

        # Limpa pasta antiga se existir
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(os.path.join(temp_dir, "videos"), exist_ok=True)

        # Copiar vídeos
        for v in videos:
            shutil.copy(os.path.join(base_dir, v), os.path.join(temp_dir, "videos", v))
        logs.append(f"🎞️ {len(videos)} vídeos copiados para exportação")

        # Copiar trilha se houver
        if trilha_path:
            shutil.copy(trilha_path, os.path.join(temp_dir, "audio.mp3"))
            logs.append("🎵 Trilha sonora incluída")

        # Copiar marca d'água se houver
        if marca_path:
            shutil.copy(marca_path, os.path.join(temp_dir, "overlay.png"))
            logs.append("🌊 Marca d'água incluída")

        # Criar metadata.json
        metadata = {
            "transicao": "manual",
            "clips": videos,
            "trilha": bool(trilha_path),
            "marca": bool(marca_path)
        }
        with open(os.path.join(temp_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        logs.append("📄 Arquivo de metadados criado")

        # Compactar em ZIP
        zip_path = os.path.join("modules", "videos_final", "projeto_capcut.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, temp_dir)
                    zipf.write(full_path, rel_path)
        logs.append(f"✅ Projeto CapCut exportado: {zip_path}")
        return {"logs": logs, "arquivo": zip_path}
    except Exception as e:
        return {"logs": [f"❌ Erro ao exportar projeto: {str(e)}"]}
