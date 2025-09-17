import os
from modules.config import get_config

def get_paths() -> dict:
    base = get_config("pasta_salvar")
    paths = {
        "base": base,
        "imagens": os.path.join(base, "imagens"),
        "audios": os.path.join(base, "audios_narracoes"),
        "legendas_ass": os.path.join(base, "legendas_ass"),
        "legendas_srt": os.path.join(base, "legendas_srt"),
        "videos_cenas": os.path.join(base, "videos_cenas"),
        "videos_final": os.path.join(base, "videos_final"),
        "cenas": os.path.join(os.getcwd(), "cenas.json"),
        "cenas_com_imagens": os.path.join(base, "cenas_com_imagens.json"),
        "nome_video": os.path.join(os.getcwd(), "ultimo_nome_video.txt"),
    }
    return paths