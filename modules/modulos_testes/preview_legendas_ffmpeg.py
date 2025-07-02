import os
import subprocess
from modules.gerar_ASS import get_paths

paths = get_paths()
audio_path = os.path.join(paths["audios"], "exemplo.mp3")
output_dir = os.path.join(paths["legendas"], "videos_preview")
os.makedirs(output_dir, exist_ok=True)

# Gera vídeo base de fundo preto + áudio
temp_video_base = os.path.join(output_dir, "base.mp4")
cmd_base = [
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=5",
    "-i", audio_path,
    "-c:v", "libx264", "-c:a", "aac",
    "-shortest", temp_video_base
]
subprocess.run(cmd_base, check=True)

arquivos_ass = [f for f in os.listdir(paths["legendas"]) if f.endswith(".ass")]

def embutir_legenda_ass_ffmpeg(video_entrada, legenda_ass, video_saida):
    vei = os.path.abspath(video_entrada)
    leg = os.path.abspath(legenda_ass)
    out = os.path.abspath(video_saida)
    leg = leg.replace("\\", "\\\\").replace(":", "\\:")
    filtro = f"subtitles='{leg}'"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "info", "-y",
        "-i", vei,
        "-vf", filtro,
        "-c:a", "copy",
        out
    ]
    print("🎬 Gerando:", out)
    subprocess.run(cmd, check=True)

for arquivo in arquivos_ass:
    legenda_path = os.path.join(paths["legendas"], arquivo)
    saida_video = os.path.join(output_dir, arquivo.replace(".ass", ".mp4"))
    try:
        embutir_legenda_ass_ffmpeg(temp_video_base, legenda_path, saida_video)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao gerar {saida_video}:", e)

print(f"✅ {len(arquivos_ass)} vídeos gerados em: {output_dir}")