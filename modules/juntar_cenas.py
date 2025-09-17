
from modules.paths import get_paths
import json, subprocess, os
from modules.config import get_config

path = get_paths()

def montar_uma_cena(idx, config):

    imagem_path   = os.path.join(path["imagens"],  f"imagem{idx + 1}.jpg")
    audio_path    = os.path.join(path["audios"],   f"narracao{idx + 1}.mp3")
    legenda_path  = os.path.join(path["legendas_ass"], f"legenda{idx + 1}.ass")
    video_efeito  = os.path.join(path["videos_cenas"],    f"temp_efeito_{idx}.mp4")

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

    # Redimensionar para 1080x1920 se necessário
    video_resized=os.path.join(path["videos_cenas"], f"temp_resized_{idx}.mp4")
    comando_resize=[
        "ffmpeg", "-y", "-i", video_efeito,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "copy",
        video_resized
    ]
    print("🔁 Redimensionando vídeo para 1080x1920...")

    # 2️⃣ Aplicar legenda (se habilitada)
    if usar_legenda and os.path.exists(legenda_path):
        # Ajustar a altura da legenda com base na posição selecionada
        ajustar_marginv_ass(legenda_path, pos_legenda)
        video_legenda = os.path.join(path["videos_cenas"], f"temp_legenda_{idx}.mp4")
        print("posição da legenda é: ", pos_legenda)
        adicionar_legenda_ass(video_efeito, legenda_path, pos_legenda, video_legenda)
    else:
        video_legenda = video_efeito

    # 3️⃣ Verificação se vídeo com legenda existe
    if not os.path.exists(video_legenda):
        raise FileNotFoundError(f"❌ Arquivo não criado: {video_legenda}")

    # 4️⃣ Adicionar o áudio final
    print("vai gerar o video final")
    video_final = os.path.join(path["videos_cenas"], f"video{idx + 1}.mp4")
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

def aplicar_efeito_na_imagem(imagem_path, audio_path, output_path, efeito, config_efeito):
    import subprocess

    def join_filters(*args):
        return ",".join(filter(None, args))

    fator = float(config_efeito.get("fator", 1.2))
    modo = config_efeito.get("modo", "in")
    fps = int(config_efeito.get("fps", 25))
    direcao = config_efeito.get("direcao", "left")
    intensidade = int(config_efeito.get("intensidade", 3))
    tempos_zoom = config_efeito.get("tempos", "")

    duracao = obter_duracao_em_segundos(audio_path)
    total_frames = duracao * fps

    if efeito == "zoom":
        if modo == "in":
            z_expr = f"1+({fator}-1)*on/{total_frames}"
        else:
            z_expr = f"{fator}-({fator}-1)*on/{total_frames}"
        filtro = join_filters(
            "scale=8000:-1",
            f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=25:fps={fps}:s=1080x1920",
            "format=yuv420p"
        )

    elif efeito == "espelho":
        filtro = "hflip,format=yuv420p"

    elif efeito == "escurecer":
        filtro = "eq=brightness=-0.3,format=yuv420p"

    elif efeito == "preto_branco":
        filtro = "format=gray,format=yuv420p"

    elif efeito == "fade_in":
        filtro = f"fade=t=in:st=0:d=1,format=yuv420p"

    elif efeito == "fade_out":
        filtro = f"fade=t=out:st={duracao-1}:d=1,format=yuv420p"

    elif efeito == "blur_pulse":
        filtro = "gblur=sigma='abs(sin(t*2))*5',format=yuv420p"

    elif efeito == "shake_horizontal":
        filtro = "crop=iw-4:ih:x='mod(t*30\\,4)':y=0,format=yuv420p"

    elif efeito == "shake_vertical":
        filtro = "crop=iw:ih-4:x=0:y='mod(t*30\\,4)',format=yuv420p"

    elif efeito == "pulsar_brilho":
        filtro = "eq=brightness='sin(t*2)*0.2',format=yuv420p"

    elif efeito == "cor_oscila":
        filtro = "hue=s='abs(sin(t*2))',format=yuv420p"

    elif efeito == "giro_leve":
        filtro = "rotate='0.05*sin(t*1.5)':ow=rotw(iw):oh=roth(ih),format=yuv420p"

    elif efeito == "loop_colorido":
        filtro = "hue=s='0.5+0.5*sin(t)',format=yuv420p"

    elif efeito == "transparente_pulse":
        filtro = "format=yuva420p,fade=in:st=0:d=0.5,fade=out:st=0.5:d=0.5,format=yuv420p"

    elif efeito == "slide":
        zoom = "scale=8000:-1"
        if direcao == "left":
            movimento = f"crop=iw:ih:x='-t*100':y=0"
        elif direcao == "right":
            movimento = f"crop=iw:ih:x='t*100':y=0"
        elif direcao == "up":
            movimento = f"crop=iw:ih:x=0:y='-t*100'"
        elif direcao == "down":
            movimento = f"crop=iw:ih:x=0:y='t*100'"
        else:
            movimento = ""
        filtro = join_filters(zoom, movimento, "format=yuv420p")

    elif efeito == "tremor":
        shift = max(2, min(intensidade, 20))
        filtro = f"crop=iw-{shift}:ih-{shift}:x='mod(t*60,{shift})':y='mod(t*60,{shift})',format=yuv420p"

    elif efeito == "zoom_rapido_em_partes":
        filtro = f"scale=8000:-1,format=yuv420p"
        tempos = [t.strip() for t in tempos_zoom.split(",") if t.strip()]
        if tempos:
            overlays = []
            for i, tempo in enumerate(tempos):
                try:
                    t = float(tempo)
                    overlays.append(
                        f"zoompan=z='{fator}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:fps={fps}:s=1080x1920:st={int(t*fps)}"
                    )
                except:
                    continue
            if overlays:
                filtro = join_filters("scale=8000:-1", *overlays, "format=yuv420p")

    elif efeito == "distorcao_tv":
        filtro = "tblend=all_mode=difference,format=yuv420p"

    else:
        filtro = "format=yuv420p"

    cmd = [
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
    result = subprocess.run(cmd, capture_output=True, text=True)
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

def adicionar_trilha_sonora(video_path, trilha_path, output_path, volume=1.0):
    dur_video = obter_duracao_em_segundos(video_path)
    dur_trilha = obter_duracao_em_segundos(trilha_path)

    if dur_trilha <= 0:
        raise ValueError("Duração da trilha inválida.")

    if dur_trilha < dur_video:
        loops = int(dur_video // dur_trilha) + 1
        with open("trilha_concat.txt", "w", encoding="utf-8") as f:
            f.writelines([f"file '{os.path.abspath(trilha_path)}'\n"] * loops)

        trilha_expandida = "trilha_expandida.mp3"
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", "trilha_concat.txt", "-c", "copy", trilha_expandida
        ], check=True)
    else:
        trilha_expandida = trilha_path

    temp_output=output_path.replace(".mp4", "_temp.mp4")

    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", trilha_expandida,
        "-filter_complex",
        f"[1:a]volume={volume}[trilha];[0:a][trilha]amix=inputs=2:duration=first[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", temp_output
    ], check=True)

    os.replace(temp_output, output_path)

    if trilha_expandida == "trilha_expandida.mp3":
        os.remove("trilha_concat.txt")
        os.remove(trilha_expandida)


    print(f"🎵 Trilha adicionada com volume {volume*100:.0f}% → {output_path}")

def adicionar_marca_dagua(video_path, imagem_path, output_path, opacidade=1.0):
    """
    Sobrepõe uma imagem PNG com opacidade sobre o vídeo.
    A imagem deve ser 1080x1920 com fundo transparente.
    """
    temp_output = output_path.replace(".mp4", "_temp.mp4")
    print("Opacidade selecionada:> ", opacidade)

    video_w, video_h=get_resolution(video_path)
    marca_w, marca_h=get_resolution(imagem_path)

    # Redimensiona a marca d’água para o mesmo tamanho
    marca_path_redimensionada=imagem_path.replace(".png", "_resize.png")
    redimensionar_marca(imagem_path, video_w, video_h, marca_path_redimensionada)

    print(f"📹 Resolução do vídeo: {video_w}x{video_h}")
    print(f"🖼️ Resolução da marca d'água: {marca_w}x{marca_h}")


    cmd=[
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", marca_path_redimensionada,
        "-filter_complex",
        f"[1:v]format=argb,colorchannelmixer=aa={opacidade},format=rgba[marca];"
        "[0:v][marca]overlay=0:0",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        temp_output
    ]

    subprocess.run(cmd, check=True)
    os.replace(temp_output, output_path)

    print(f"🖼️ Marca d'água aplicada com opacidade {opacidade:.2f}")

def get_resolution(path):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json", path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        info = json.loads(result.stdout)
        width = info["streams"][0]["width"]
        height = info["streams"][0]["height"]
        return width, height
    except Exception as e:
        print(f"Erro ao obter resolução de {path}: {e}")
        return None, None

def redimensionar_marca(marca_path, largura, altura, marca_redimensionada_path):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", marca_path,
        "-vf", f"scale={largura}:{altura}",
        "-q:v", "1",
        marca_redimensionada_path
    ], check=True)
    print(f"🧩 Marca d'água redimensionada para {largura}x{altura}")

def ajustar_marginv_ass(ass_path, posicao):
    """Atualiza dinamicamente o MarginV do estilo principal no .ASS com Alignment=2 fixo."""
    posicoes_marginv = {
        "inferior": 100,
        "central": 900,
        "central-1": 700,
        "central-2": 500,
        "central-3": 300,
    }

    nova_marginv = posicoes_marginv.get(posicao)

    try:
        with open(ass_path, encoding="utf-8") as f:
            linhas = f.readlines()

        novas_linhas = []
        for linha in linhas:
            if linha.strip().startswith("Style:"):
                partes = linha.strip().split(",")
                if len(partes) >= 21:
                    partes[21] = str(nova_marginv)  # MarginV
                    partes[18] = "2"  # Alignment = 2 (central horizontal inferior)
                    linha = ",".join(partes) + "\n"
            novas_linhas.append(linha)

        with open(ass_path, "w", encoding="utf-8") as f:
            f.writelines(novas_linhas)

    except Exception as e:
        print(f"❌ Erro ao ajustar MarginV do .ASS: {e}")

