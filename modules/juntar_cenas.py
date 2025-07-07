"""Rotinas para juntar cenas individuais em um único vídeo final, com transições funcionais e correções de dimensionamento."""

import os
import json
from moviepy import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    vfx

)
from moviepy.video.fx import Resize, FadeIn, FadeOut, SlideIn, SlideOut
from modules.config import get_config

# Configurações de diretórios
PASTA_BASE   = get_config("pasta_salvar") or "."
PASTA_VIDEOS = os.path.join(PASTA_BASE, "videos_cenas")
PASTA_SAIDA  = os.path.join(PASTA_BASE, "videos_final")
os.makedirs(PASTA_SAIDA, exist_ok=True)


def aplicar_efeito(clip, efeito, config=None):
    """Aplica um efeito ao clipe usando API MoviePy v2.2.1+."""
    print(f"[EFEITO] {efeito}")
    # Preto e branco
    if efeito == "preto_branco":
        return clip.with_effects([vfx.BlackAndWhite()])

    # Espelho horizontal
    if efeito == "espelho":
        return clip.with_effects([vfx.MirrorX()])

    # Escurecer
    if efeito == "escurecer":
        return clip.with_effects([vfx.MultiplyColor(0.5)])

    # Zoom Ken Burns
    if efeito == "zoom":
        cfg   = config or {}
        raw   = str(cfg.get("fator", 1.2)).replace(",", ".")
        fator = float(raw)
        modo  = cfg.get("modo", "in")  # 'in' ou 'out'
        dur   = clip.duration
        w, h  = clip.size

        if modo == "in":
            # Zoom in: inicia em 1.0 e cresce até 'fator', sem recorte
            zoom_func = lambda t: 1.0 + (fator - 1.0) * (t / dur)
            return clip.with_effects([Resize(zoom_func)])
        else:
            # Zoom out: inicia em 'fator' e decresce até 1.0, com recorte
            zoom_func = lambda t: fator - (fator - 1.0) * (t / dur)
            zoomed = clip.with_effects([Resize(zoom_func)])
            # centraliza e mantém quadro fixo
            def offset(t):
                s = zoom_func(t)
                return (-(s - 1.0) * w / 2, -(s - 1.0) * h / 2)
            return CompositeVideoClip(
                [zoomed.with_position(offset)],
                size=(w, h)
            ).with_duration(dur)

    # Sem efeito específico
    return clip


def aplicar_transicao(prev, curr, tipo, dur):
    """
    Recebe:
      prev, curr: VideoFileClip
      tipo: 'crossfade'|'fade'|'slide'|'overlay' ou qualquer outro para cut
      dur: duração da transição em segundos
    Retorna:
      (first, second) — dois clipes que, quando concatenados com method='compose',
      geram a transição desejada.
    """
    w, h = prev.size

    # 1) Fade / Crossfade para preto
    if tipo in ("crossfade", "fade"):
        # fade-out no final de prev
        first = prev.with_effects([FadeOut(dur)])
        # fade-in no início de curr, começando quando prev terminar
        second = curr.with_effects([FadeIn(dur)]).with_start(prev.duration)
        return first, second

    # 3) Slide
    if tipo == "slide":
        # 2.a) Slide-out do prev pela esquerda
        prev_slide=prev.with_effects([SlideOut(dur, side="left")])
        # 2.b) Slide-in do curr pela direita, com overlap de 'dur' segundos
        curr_slide=curr.with_effects([SlideIn(dur, side="right")]) \
            .with_start(prev.duration - dur)
        # 2.c) Composição dos dois para gerar o período de overlap
        comp=CompositeVideoClip(
            [prev_slide, curr_slide],
            size=(w, h)
        ).with_duration(prev.duration + curr.duration - dur)
        # 2.d) Resto de curr que não estava no overlap
        if curr.duration > dur:
            rest=curr.subclipped(dur, curr.duration).with_start(prev.duration)
        else:
            rest=curr.with_start(prev.duration)
        return comp, rest

    # 4) Overlay (fade anterior + mostra próximo staticamente)
    if tipo == "overlay":
        curr_ov=curr.with_start(prev.duration - dur) \
            .with_opacity(0.7) \
            .with_position(("center", "center"))
        comp=CompositeVideoClip(
            [prev, curr_ov],
            size=(w, h)
        ).with_duration(prev.duration + curr.duration - dur)
        if curr.duration > dur:
            rest=curr.subclipped(dur, curr.duration).with_start(prev.duration)
        else:
            rest=curr.with_start(prev.duration)
        return comp, rest

    # 4) Cut seco (sem transição)
    second = curr.with_start(prev.duration)
    return prev, second


def run_juntar_cenas(
    cenas_param: str,
    usar_musica=False,
    trilha_path=None,
    volume=0.2,
    usar_watermark=False,
    marca_path=None,
    opacidade=0.3,
    posicao=("right","bottom")
):
    logs = []
    try:
        cfg_list = json.loads(cenas_param)
        arquivos = sorted(os.listdir(PASTA_VIDEOS))
        clips = []

        # Carrega e aplica efeitos
        for idx, fname in enumerate(arquivos):
            path = os.path.join(PASTA_VIDEOS, fname)
            print(f"[CENA] {idx+1}: {fname}")
            clip = VideoFileClip(path)
            cfg  = cfg_list[idx] if idx < len(cfg_list) else {}
            clip = aplicar_efeito(clip, cfg.get("efeito"), cfg.get("config"))
            logs.append(f"🔧 Cena {idx+1}: efeito={cfg.get('efeito','nenhum')}")
            clips.append(clip)

        # Aplica transições e concatena
        merged = []
        for i, clip in enumerate(clips):
            if i == 0:
                merged.append(clip)
            else:
                prev     = merged.pop()
                cfg_prev = cfg_list[i-1]
                tipo     = cfg_prev.get("transicao", "cut")
                dur      = float(cfg_prev.get("duracao", 0.5))
                logs.append(f"🔀 Transição {i}->{i+1}: {tipo} ({dur}s)")
                first, second = aplicar_transicao(prev, clip, tipo, dur)
                merged.extend([first, second])

        print("[CONCAT] concatenando...")
        final = concatenate_videoclips(merged)
        logs.append(f"🎞️ {len(clips)} cenas juntadas")

        # Trilha sonora
        if usar_musica and trilha_path and os.path.isfile(trilha_path):
            print(f"[ÁUDIO] {trilha_path}")
            audio = AudioFileClip(trilha_path).volumex(volume)
            final = final.with_audio(audio)
            logs.append("🎵 Trilha aplicada")

        # Marca d'água
        if usar_watermark and marca_path and os.path.isfile(marca_path):
            print(f"[WATERMARK] {marca_path}")
            marca = ImageClip(marca_path)
            marca = marca.with_duration(final.duration).resized(height=100)
            marca = marca.with_opacity(opacidade).with_position(posicao)
            final = CompositeVideoClip([final, marca], size=(w, h))
            logs.append("🌊 Marca d'água aplicada")

        # Salva vídeo
        out = os.path.join(PASTA_SAIDA, f"video_final_{int(final.duration)}s.mp4")
        print(f"[SAVE] {out}")
        final.write_videofile(
            out,
            fps=24,
            codec="libx264",
            preset="ultrafast",
            audio_codec="aac",
            logger=None
        )
        logs.append(f"✅ Salvo em: {out}")
        return {"logs": logs}
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"logs": [f"❌ Erro: {e}"]}
