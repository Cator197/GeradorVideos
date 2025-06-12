import os
import json
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeAudioClip,
    CompositeVideoClip, TextClip, concatenate_videoclips
)
from moviepy.video.tools.subtitles import SubtitlesClip

ARQUIVO_JSON = "cenas_com_legendas.json"
PASTA_SAIDA = "videos_finais"
FPS = 30

def srt_from_legendas(legendas, temp_srt_path):
    with open(temp_srt_path, "w", encoding="utf-8") as f:
        for i, l in enumerate(legendas, 1):
            start = l['inicio']
            end = l['fim']
            text = l['texto']
            start_srt = segundos_para_srt(start)
            end_srt = segundos_para_srt(end)
            f.write(f"{i}\n{start_srt} --> {end_srt}\n{text}\n\n")

def segundos_para_srt(seg):
    h = int(seg // 3600)
    m = int((seg % 3600) // 60)
    s = int(seg % 60)
    ms = int((seg - int(seg)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def carregar_audio(audio_url):
    local = audio_url if os.path.exists(audio_url) else None
    return AudioFileClip(local) if local else None

def baixar_para_local(url, nome_arquivo):
    caminho = os.path.join("cache", nome_arquivo)
    if not os.path.exists("cache"):
        os.makedirs("cache")
    if not os.path.exists(caminho):
        import requests
        r = requests.get(url)
        with open(caminho, "wb") as f:
            f.write(r.content)
    return caminho

def montar_video(cena, indice):
    print(f"🎬 Montando cena {indice + 1}...")

    video_path = baixar_para_local(cena["video_url"], f"cena{indice+1}_base.mp4")
    video = VideoFileClip(video_path)

    audios = []

    # Narração
    if "audio_narracao_url" in cena:
        path = baixar_para_local(cena["audio_narracao_url"], f"cena{indice+1}_narracao.mp3")
        audios.append(AudioFileClip(path))

    # Trilha sonora
    if "trilha_sonora_audio" in cena:
        path = baixar_para_local(cena["trilha_sonora_audio"]["audio_url"], f"cena{indice+1}_trilha.mp3")
        audios.append(AudioFileClip(path).volumex(0.4))  # som de fundo

    # Efeitos sonoros
    for efeito in cena.get("efeitos_aplicados", []):
        if os.path.exists(efeito["arquivo"]):
            audios.append(AudioFileClip(efeito["arquivo"]))

    # Lipsyncs (opcional)
    lipsyncs = []
    for lip in cena.get("lipsyncs", []):
        path = baixar_para_local(lip["video_lipsync_url"], f"cena{indice+1}_{lip['personagem']}_lip.mp4")
        lipsync_clip = VideoFileClip(path).set_position(("center", "bottom")).resize(height=video.h // 3)
        lipsyncs.append(lipsync_clip)

    # Legendas
    legenda_path = f"legenda_temp_{indice+1}.srt"
    srt_from_legendas(cena["legendas"], legenda_path)
    generator = lambda txt: TextClip(txt, font='Arial', fontsize=32, color='white', bg_color='black')
    legendas = SubtitlesClip(legenda_path, generator)

    # Composição final
    audio_final = CompositeAudioClip(audios).set_duration(video.duration)
    video_final = CompositeVideoClip([video, *lipsyncs, legendas.set_position(("center", "bottom"))])
    video_final = video_final.set_audio(audio_final)

    output_path = os.path.join(PASTA_SAIDA, f"cena_{indice+1}.mp4")
    if not os.path.exists(PASTA_SAIDA):
        os.makedirs(PASTA_SAIDA)

    video_final.write_videofile(output_path, fps=FPS, codec='libx264', audio_codec='aac')
    print(f"✅ Cena {indice + 1} salva em {output_path}")

if __name__ == "__main__":
    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    for i, cena in enumerate(cenas):
        montar_video(cena, i)
