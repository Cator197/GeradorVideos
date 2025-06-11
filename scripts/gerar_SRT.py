import os
import json
from faster_whisper import WhisperModel

# Caminhos
ARQUIVO_CENAS = "cenas_com_imagens.json"
PASTA_AUDIOS = "audios_narracoes"
PASTA_SRTS = "legendas_srt"
os.makedirs(PASTA_SRTS, exist_ok=True)

# Carrega modelo Whisper
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
    print(f"✅ Legenda salva: {srt_path}")

def processar_legendas(index=None):
    with open(ARQUIVO_CENAS, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    if index is not None:
        audio_path = os.path.join(PASTA_AUDIOS, f"narracao{index + 1}.mp3")
        srt_path = os.path.join(PASTA_SRTS, f"legenda{index + 1}.srt")
        if os.path.exists(audio_path):
            print(f"🎙️ Gerando legenda para narração {index + 1}")
            gerar_srt_por_palavra(audio_path, srt_path)
        else:
            print(f"⚠️ Áudio não encontrado: {audio_path}")
    else:
        for i, _ in enumerate(cenas):
            audio_path = os.path.join(PASTA_AUDIOS, f"narracao{i + 1}.mp3")
            srt_path = os.path.join(PASTA_SRTS, f"legenda{i + 1}.srt")
            if os.path.exists(audio_path):
                print(f"🎙️ Gerando legenda para narração {i + 1}")
                gerar_srt_por_palavra(audio_path, srt_path)
            else:
                print(f"⚠️ Áudio não encontrado: {audio_path}")

if __name__ == "__main__":
    opcao = input("🔹 Gerar legenda para [T]odas as cenas ou [U]ma específica? (T/U): ").strip().lower()

    if opcao == "u":
        try:
            indice = int(input("Digite o número da cena (ex: 1 para narracao1.mp3): ").strip()) - 1
            processar_legendas(index=indice)
        except ValueError:
            print("❌ Entrada inválida. Use um número inteiro.")
    else:
        processar_legendas()
