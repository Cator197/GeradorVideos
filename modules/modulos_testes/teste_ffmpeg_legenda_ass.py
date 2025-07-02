import subprocess
import os

# Ajuste os caminhos abaixo conforme seu ambiente
video_entrada = r"C:\Users\caiod\Desktop\Nova pasta\gerador\videos_cenas\temp_video1.mp4"
legenda_ass   = r"C:\Users\caiod\Desktop\Nova pasta\gerador\legendas_ass\legenda1.ass"
video_saida   = r"C:\Users\caiod\Desktop\Nova pasta\gerador\videos_cenas\teste_video1.mp4"

# Escapando o caminho da legenda para o filtro do FFmpeg
path_legenda = os.path.abspath(legenda_ass).replace("\\", "/").replace(":", "\\:").replace(" ", "\\ ")

filtro = f"subtitles={path_legenda}"

comando = [
    "ffmpeg", "-hide_banner", "-loglevel", "info", "-y",
    "-i", video_entrada,
    "-vf", filtro,
    "-c:a", "copy",
    video_saida
]

print(">> Executando comando FFmpeg:")
print(" ".join(comando))
print()

try:
    subprocess.run(comando, check=True)
    print("✅ Sucesso! Legenda embutida.")
except subprocess.CalledProcessError as e:
    print("❌ Erro ao executar FFmpeg.")
    print("Código de erro:", e.returncode)
    print("Comando:", e.cmd)
