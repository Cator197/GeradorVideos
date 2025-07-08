import os
import subprocess
from modules.config import get_config
import shlex
import subprocess
import shutil

def montar_uma_cena(idx, config):
    base = get_config("pasta_salvar") or os.getcwd()
    pasta_imagens = os.path.join(base, "imagens")
    pasta_audios = os.path.join(base, "audios_narracoes")
    pasta_legendas = os.path.join(base, "legendas_ass")
    pasta_saida = os.path.join(base, "videos_cenas")

    imagem_path = os.path.join(pasta_imagens, f"imagem{idx + 1}.jpg")
    audio_path = os.path.join(pasta_audios, f"narracao{idx + 1}.mp3")
    legenda_path = os.path.join(pasta_legendas, f"legenda{idx + 1}.ass")
    video_efeito = os.path.join(pasta_saida, f"temp_efeito_{idx}.mp4")

    usar_legenda=config.get("usarLegenda", False)
    pos_legenda=config.get("posicaoLegenda", "inferior")

    print(f"[DEBUG] Cena {idx + 1} - config recebido:", config)

    # 1. Aplicar efeito
    print("🌀 Efeito:", config.get("efeito"))

    aplicar_efeito_na_imagem(
        imagem_path=imagem_path,
        audio_path=audio_path,
        output_path=video_efeito,
        efeito=config.get("efeito"),
        config_efeito=config.get("config", {})
    )
    print("Legenda path:", legenda_path)

    if usar_legenda and os.path.exists(legenda_path):
        video_legenda=os.path.join(pasta_saida, f"temp_legenda_{idx}.mp4")
        adicionar_legenda_ass(video_efeito, legenda_path, pos_legenda, video_legenda)
    else:
        video_legenda=video_efeito

    if not os.path.exists(video_efeito):
        raise FileNotFoundError(f"❌ Arquivo não criado: {video_legenda}")

    return video_legenda




# ---------------------- FUNÇÕES AUXILIARES -----------------------------------------------------------------------

def adicionar_legenda_ass(input_path, legenda_path, posicao, output_path):
    # Corrigir e escapar caminho da legenda
    vei = os.path.abspath(input_path)
    leg = os.path.abspath(legenda_path)
    out = os.path.abspath(output_path)

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


def obter_duracao_em_segundos(path):
    """Usa ffprobe para obter a duração do vídeo/áudio em segundos."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        try:
            duracao = float(json.loads(result.stdout)["format"]["duration"])
            return duracao
        except Exception:
            pass
    return 5  # valor padrão de segurança

import os
import subprocess
import json
from modules.config import get_config

def aplicar_efeito_na_imagem(imagem_path, audio_path, output_path, efeito, config_efeito):
    import subprocess
    import os

    fator = float(config_efeito.get("fator", 1.2))
    modo = config_efeito.get("modo", "in")
    fps = int(config_efeito.get("fps", 25))
    duracao = obter_duracao_em_segundos(audio_path)
    total_frames = duracao * fps

    if efeito == "zoom":
        if modo == "in":
            z_expr = f"1+({fator}-1)*on/{total_frames}"
        else:
            z_expr = f"{fator}-({fator}-1)*on/{total_frames}"

        filtro = (
            "scale=8000:-1,"
            f"zoompan=z='{z_expr}':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=25:fps={fps}:s=1080x1920,"
            "format=yuv420p"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", str(fps),
            "-i", imagem_path,
            "-vf", filtro,
            "-t", str(duracao),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            output_path
        ]



    elif efeito in ["espelho", "escurecer", "preto_branco"]:

        filtro={

            "espelho": "hflip",

            "escurecer": "eq=brightness=-0.3",

            "preto_branco": "format=gray"

        }[efeito]

        # Como padronizamos para .mp4 com duração do áudio, aplicamos com loop:

        filtro+=",format=yuv420p"


    else:

        filtro="format=yuv420p"

    cmd=[

        "ffmpeg", "-y",

        "-loop", "1",

        "-framerate", str(fps),

        "-i", imagem_path,

        "-vf", filtro,

        "-t", str(duracao),

        "-c:v", "libx264",

        "-preset", "ultrafast",

        "-crf", "20",

        output_path

    ]

    print("🎬 FFmpeg aplicando efeito:", " ".join(cmd))

    result=subprocess.run(cmd, capture_output=True, text=True)

    print("STDERR FFmpeg:", result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"❌ Erro ao aplicar efeito: {result.stderr}")

    return output_path


def montar_video_com_audio(base_visual_path, audio_path, output_path):
    ext = os.path.splitext(base_visual_path)[-1].lower()
    if ext == ".jpg":
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", base_visual_path,
            "-i", audio_path,
            "-shortest",
            "-c:v", "libx264", "-tune", "stillimage", "-preset", "ultrafast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            output_path
        ]
    elif ext == ".mp4":
        cmd = [
            "ffmpeg", "-y",
            "-i", base_visual_path,
            "-i", audio_path,
            "-shortest",
            "-c:v", "copy",
            "-c:a", "aac",
            output_path
        ]
    else:
        raise ValueError(f"❌ Formato visual não suportado: {ext}")

    print("🎬 FFmpeg final video:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("STDERR FFmpeg:", result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"❌ Erro ao montar vídeo com áudio: {result.stderr}")

    return output_path
