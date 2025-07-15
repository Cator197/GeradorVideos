"""Utilitário para remover trechos silenciosos dos áudios de narração."""

import os
from pydub import AudioSegment, silence
from modules.config import get_config
from modules.paths import get_paths

path = get_paths()

def remover_silencios(min_silence: float = 0.5):
    """Remove trechos silenciosos de todos os áudios MP3 encontrados."""
    base_path = get_config("pasta_salvar") or os.path.join(os.getcwd(), "modules")
    pasta = path["audios_narracoes"]

    if not os.path.exists(pasta):
        return {"status": "erro", "error": f"Pasta não encontrada: {pasta}"}

    arquivos = [f for f in os.listdir(pasta) if f.endswith(".mp3")]
    count = 0
    logs = [f"🔍 Iniciando remoção de silêncio em {len(arquivos)} arquivos..."]

    for nome in arquivos:
        caminho = os.path.join(pasta, nome)
        try:
            logs.append(f"🔊 Processando {nome}")
            audio = AudioSegment.from_file(caminho, format="mp3")

            # Ajuste dinâmico do limiar de silêncio com base no volume do áudio
            silence_thresh = audio.dBFS - 14
            min_silence_len = int(min_silence * 1000)  # em ms

            chunks = silence.split_on_silence(
                audio,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh,
                keep_silence=50
            )

            if not chunks:
                logs.append(f"⚠️ Nenhum áudio detectado em {nome}")
                continue

            novo_audio = AudioSegment.silent(duration=0)
            for chunk in chunks:
                novo_audio += chunk

            novo_audio.export(caminho, format="mp3")
            count += 1
            logs.append(f"✅ Silêncio removido de {nome}")

        except Exception as e:
            logs.append(f"❌ Erro ao processar {nome}: {e}")
            continue

    logs.append(f"🏁 Processamento concluído. {count} arquivos alterados.")
    return {"status": "ok", "arquivos": count, "logs": logs}
