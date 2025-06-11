import os
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx

PASTA_CENAS = "videos_finais"
ARQUIVO_SAIDA = "video_final_completo.mp4"
DURACAO_FADE = 1.0  # segundos

def listar_arquivos_ordenados(pasta):
    arquivos = [f for f in os.listdir(pasta) if f.endswith(".mp4")]
    return sorted(arquivos, key=lambda x: int(x.split("_")[1].split(".")[0]))

def unir_cenas_com_transicao():
    arquivos = listar_arquivos_ordenados(PASTA_CENAS)
    if not arquivos:
        print("❌ Nenhum arquivo de cena encontrado.")
        return

    clips = []
    for i, arquivo in enumerate(arquivos):
        caminho = os.path.join(PASTA_CENAS, arquivo)
        clip = VideoFileClip(caminho)

        if i > 0:
            clip = clip.fadein(DURACAO_FADE)
        if i < len(arquivos) - 1:
            clip = clip.fadeout(DURACAO_FADE)

        clips.append(clip)

    video_final = concatenate_videoclips(clips, method="compose")
    video_final.write_videofile(ARQUIVO_SAIDA, codec="libx264", audio_codec="aac", fps=30)

    print(f"\n✅ Vídeo final exportado como {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    unir_cenas_com_transicao()
