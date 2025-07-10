import os
import subprocess
from modules.config import get_config
import shlex
import subprocess
import shutil

def montar_uma_cena(idx, config):
    base = get_config("pasta_salvar") or os.getcwd()
    pasta_imagens  = os.path.join(base, "imagens")
    pasta_audios   = os.path.join(base, "audios_narracoes")
    pasta_legendas = os.path.join(base, "legendas_ass")
    pasta_saida    = os.path.join(base, "videos_cenas")

    imagem_path   = os.path.join(pasta_imagens,  f"imagem{idx + 1}.jpg")
    audio_path    = os.path.join(pasta_audios,   f"narracao{idx + 1}.mp3")
    legenda_path  = os.path.join(pasta_legendas, f"legenda{idx + 1}.ass")
    video_efeito  = os.path.join(pasta_saida,    f"temp_efeito_{idx}.mp4")

    usar_legenda  = config.get("usarLegenda", False)
    pos_legenda   = config.get("posicaoLegenda", "inferior")

    print("Pasta salvar:", get_config("pasta_salvar"))
    print("JSON cenas:", os.path.join(get_config("pasta_salvar") or ".", "cenas_com_imagens.json"))

    print(f"[DEBUG] Cena {idx + 1} - config recebido:", config)

    # 1️⃣ Aplicar efeito visual (zoom, pb, escurecer, etc.)
    print("🌀 Efeito:", config.get("efeito"))
    aplicar_efeito_na_imagem(
        imagem_path=imagem_path,
        audio_path=audio_path,
        output_path=video_efeito,
        efeito=config.get("efeito"),
        config_efeito=config.get("config", {})
    )

    # 2️⃣ Aplicar legenda (se habilitada)
    if usar_legenda and os.path.exists(legenda_path):
        video_legenda = os.path.join(pasta_saida, f"temp_legenda_{idx}.mp4")
        adicionar_legenda_ass(video_efeito, legenda_path, pos_legenda, video_legenda)
    else:
        video_legenda = video_efeito

    # 3️⃣ Verificação se vídeo com legenda existe
    if not os.path.exists(video_legenda):
        raise FileNotFoundError(f"❌ Arquivo não criado: {video_legenda}")

    # 4️⃣ Adicionar o áudio final
    print("vai gerar o video final")
    video_final = os.path.join(pasta_saida, f"video{idx + 1}.mp4")
    adicionar_audio(video_legenda, audio_path, video_final)

    return video_final



def unir_cenas_com_transicoes(lista_videos, transicoes, output_path):
    """
    Une uma lista de vídeos com ou sem transições.
    transicoes: lista de dicionários {'tipo': 'fade'|'slideleft'|'', 'duracao': float}
    """
    if len(lista_videos) < 2:
        raise ValueError("É necessário pelo menos dois vídeos para unir.")

    print("🎬 Iniciando união das cenas em cadeia...")

    temp_resultado = lista_videos[0]

    for i in range(1, len(lista_videos)):
        entrada1 = temp_resultado
        entrada2 = lista_videos[i]
        saida_temp = output_path if i == len(lista_videos) - 1 else f"{output_path}_step_{i}.mp4"

        trans = transicoes[i - 1] if i - 1 < len(transicoes) else {"tipo": "fade", "duracao": 0.2}
        tipo = trans.get("tipo", "")
        dur = trans.get("duracao", 0.2)

        dur_video1 = obter_duracao_em_segundos(entrada1)
        offset = max(0.01, dur_video1 - dur)

        if tipo != "":
            tem_audio1 = verificar_tem_audio(entrada1)
            tem_audio2 = verificar_tem_audio(entrada2)

            filtro_video = (
                "[0:v]scale=1080:1920,setsar=1[v0];"
                "[1:v]scale=1080:1920,setsar=1[v1];"
                f"[v0][v1]xfade=transition={tipo}:duration={dur}:offset={offset}[v]"
            )

            if tem_audio1 and tem_audio2:
                filtro_audio = f"[0:a][1:a]acrossfade=d={dur}[a]"
                filtro = f"{filtro_video};{filtro_audio}"
                maps = ["-map", "[v]", "-map", "[a]"]
            else:
                filtro = filtro_video
                maps = ["-map", "[v]"]

            cmd = [
                "ffmpeg", "-y",
                "-i", entrada1,
                "-i", entrada2,
                "-filter_complex", filtro,
                *maps,
                "-c:v", "libx264", "-pix_fmt", "yuv420p"
            ]

            if tem_audio1 and tem_audio2:
                cmd += ["-c:a", "aac", "-b:a", "192k", "-ac", "2"]

            cmd += ["-movflags", "+faststart", saida_temp]

        else:
            # Concatenação direta sem transição
            with open("concat_pair.txt", "w") as f:
                f.write(f"file '{os.path.abspath(entrada1)}'\n")
                f.write(f"file '{os.path.abspath(entrada2)}'\n")
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_pair.txt",
                "-c", "copy", saida_temp
            ]

        print(f"🛠️ Executando: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        if tipo == "":
            os.remove("concat_pair.txt")

        temp_resultado = saida_temp

    print(f"✅ Vídeo final gerado: {output_path}")




# ---------------------- FUNÇÕES AUXILIARES -----------------------------------------------------------------------
def verificar_tem_audio(video_path):
    """Verifica se um arquivo de vídeo contém trilha de áudio."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "default=nw=1", video_path],
            capture_output=True, text=True
        )
        return "codec_type=audio" in result.stdout
    except Exception as e:
        print(f"⚠️ Erro ao verificar áudio em {video_path}: {e}")
        return False



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
            "-c:a", "aac", "-b:a", "192k", "-ac", "2",
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


def adicionar_audio(video_path, audio_path, output_path):
    """
    Adiciona um arquivo de áudio a um vídeo (sem reencodar o vídeo).
    Garante sincronização e compatibilidade.
    """
    print(f"🔊 Adicionando áudio: {audio_path} → {output_path}")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"❌ Vídeo não encontrado: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"❌ Áudio não encontrado: {audio_path}")

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",    # usa o vídeo do primeiro input
        "-map", "1:a:0",    # usa o áudio do segundo input
        "-c:v", "copy",     # não reencoda o vídeo
        "-c:a", "aac",      # codifica o áudio para compatibilidade ampla
        "-shortest",        # corta o vídeo ou áudio no menor dos dois
        output_path
    ]

    print("🎬 Comando FFmpeg:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    print(f"✅ Vídeo final com áudio salvo em: {output_path}")