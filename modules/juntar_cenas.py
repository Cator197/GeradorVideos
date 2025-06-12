import os
from moviepy import (
    VideoFileClip, CompositeVideoClip,
    AudioFileClip, CompositeAudioClip,
    ImageClip, vfx
)

PASTA_CENAS = "videos_cenas"
PASTA_FINAL = "videos_final"
os.makedirs(PASTA_FINAL, exist_ok=True)

# 1) Escolha de transição
tipos = ["crossfade", "slide", "scroll", "freeze", "cut"]
tipo_transicao = input(f"Tipo de transição {tipos}: ").strip().lower() or "crossfade"
duracao_trans  = float(input("Duração da transição (s): ").strip() or 1.0)

if tipo_transicao == "slide":
    slide_side = input("Slide side [left/right/top/bottom]: ").strip().lower() or "left"
elif tipo_transicao == "scroll":
    x_speed = float(input("Velocidade horizontal (px/s): ").strip() or 100)
    y_speed = float(input("Velocidade vertical   (px/s): ").strip() or 0)

# 2) Trilha de fundo opcional
usar_musica = input("Adicionar trilha de fundo? (S/N): ").strip().lower() == "s"
if usar_musica:
    arquivo_musica = input("Caminho da música de fundo: ").strip()
    volume_bg      = float(input("Volume da música (0.0–1.0): ").strip() or 0.2)

# 3) Marca-d’água opcional
usar_watermark = input("Adicionar marca-d'água? (S/N): ").strip().lower() == "s"
if usar_watermark:
    logo_path = input("Caminho do PNG da marca-d'água: ").strip() or "marca916.PNG"
    opacity   = float(input("Opacidade da marca-d'água (0.0–1.0): ").strip() or 0.3)
    position  = input("Posição da marca-d'água [(0,0)/(right,bottom)/center]: ").strip() or "(0,0)"

output_path = os.path.join(PASTA_FINAL, "video_final.mp4")

# 4) Carrega cenas e aplica transições
filenames = sorted(f for f in os.listdir(PASTA_CENAS)
                   if f.startswith("video") and f.endswith(".mp4"))

clips = []
current_start = 0.0
for fname in filenames:
    path = os.path.join(PASTA_CENAS, fname)
    clip = VideoFileClip(path)

    if tipo_transicao == "crossfade":
        if clips:
            clip = clip.with_start(current_start - duracao_trans)
            clip = vfx.CrossFadeIn(clip, duracao_trans)
            current_start += clip.duration - duracao_trans
        else:
            clip = clip.with_start(current_start)
            current_start += clip.duration

    elif tipo_transicao == "slide":
        clip = vfx.SlideIn(clip, duracao_trans, side=slide_side)
        clip = clip.with_start(current_start)
        current_start += clip.duration

    elif tipo_transicao == "scroll":
        efeito_scroll = vfx.Scroll(clip.w, clip.h, x_speed=x_speed, y_speed=y_speed)
        clip = efeito_scroll.apply(clip)
        clip = clip.with_start(current_start)
        current_start += clip.duration

    elif tipo_transicao == "freeze":
        main = clip.with_start(current_start)
        clips.append(main)
        current_start += main.duration
        frame = main.get_frame(main.duration - 1/main.fps)
        freeze = ImageClip(frame).set_duration(duracao_trans).set_start(current_start)
        clips.append(freeze)
        current_start += duracao_trans
        continue

    else:  # cut
        clip = clip.with_start(current_start)
        current_start += clip.duration

    clips.append(clip)

final = CompositeVideoClip(clips, size=clips[0].size)

# 5) Adiciona trilha de fundo
if usar_musica:
    musica = AudioFileClip(arquivo_musica).volumex(volume_bg).loop(duration=final.duration)
    final = final.with_audio(CompositeAudioClip([final.audio, musica]))

# 6) Aplica marca-d’água
if usar_watermark:
    wm = (
        ImageClip(logo_path)
        .set_duration(final.duration)
        .set_opacity(opacity)
        .set_pos(eval(position))  # ex: (0,0) ou ("right","bottom")
    )
    final = CompositeVideoClip([final, wm], size=final.size)

# 7) Exporta
final.write_videofile(output_path, fps=24, logger=None)
print(f"✅ Vídeo final gerado em: {output_path}")
