import os
import json
from faster_whisper import WhisperModel

ARQUIVO_CENAS = os.path.join(os.path.dirname(__file__), "cenas_com_imagens.json")
PASTA_AUDIOS = os.path.join(os.path.dirname(__file__), "audios_narracoes")
PASTA_SRTS   = os.path.join(os.path.dirname(__file__), "legendas_srt")
os.makedirs(PASTA_SRTS, exist_ok=True)

print("🧠 Carregando modelo Whisper...")
model = WhisperModel("medium", device="cpu", compute_type="int8")

def formatar_tempo(segundos):
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos - int(segundos)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def gerar_srt_por_palavra(audio_path, srt_path):
    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    srt_linhas = []
    contador = 1

    for segmento in segments:
        for palavra in segmento.words:
            inicio = palavra.start
            fim = palavra.end
            texto = palavra.word.strip()
            linha = f"{contador}\n{formatar_tempo(inicio)} --> {formatar_tempo(fim)}\n{texto}\n"
            srt_linhas.append(linha)
            contador += 1

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_linhas))

def run_gerar_legendas(indices):
    logs = []
    with open(ARQUIVO_CENAS, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    for i in indices:
        audio_path = os.path.join(PASTA_AUDIOS, f"narracao{i + 1}.mp3")
        srt_path = os.path.join(PASTA_SRTS, f"legenda{i + 1}.srt")
        if os.path.exists(audio_path):
            logs.append(f"📝 Gerando legenda para narração {i + 1}")
            print(f"📝 Gerando legenda para narração {i + 1}")
            gerar_srt_por_palavra(audio_path, srt_path)
            logs.append(f"✅ Legenda {i + 1} salva em {srt_path}")
            print(f"✅ Legenda {i + 1} salva em {srt_path}")
            cenas[i]["srt_path"] = srt_path
        else:
            logs.append(f"⚠️ Áudio não encontrado para narração {i + 1}")

    with open(ARQUIVO_CENAS, "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return {"logs": logs, "cenas": cenas}
