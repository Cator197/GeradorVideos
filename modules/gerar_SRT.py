import os
import json
from faster_whisper import WhisperModel
from modules.paths import get_paths

path = get_paths()

def formatar_tempo(segundos):
    """Converte segundos em formato compatível com legendas SRT.

    Parâmetros:
        segundos (float): Tempo absoluto a ser convertido.

    Retorna:
        str: Representação ``HH:MM:SS,mmm`` do tempo informado.
    """
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos - int(segundos)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def carregar_modelo():
    """Carrega o modelo Whisper utilizado para gerar as transcrições.

    Parâmetros:
        Nenhum.

    Retorna:
        WhisperModel: Instância configurada para execução em CPU.
    """
    return WhisperModel("small", device="cpu", compute_type="int8")

def gerar_srt_com_bloco(indices, palavras_por_bloco=4):
    """Gera arquivos SRT agrupando palavras em blocos definidos.

    Parâmetros:
        indices (Iterable[int]): Índices das cenas a serem processadas.
        palavras_por_bloco (int): Quantidade de palavras em cada linha gerada.

    Retorna:
        list[str]: Lista de mensagens de log descrevendo o resultado por cena.
    """

    model = carregar_modelo()
    logs = []

    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    os.makedirs(path["legendas_srt"], exist_ok=True)

    for i in indices:
        audio_path = os.path.join(path["audios"], f"narracao{i}.mp3")
        srt_path = os.path.join(path["legendas_srt"], f"legenda{i}.srt")

        if not os.path.exists(audio_path):
            logs.append(f"⚠️ Áudio {i} não encontrado.")
            continue

        segments, _ = model.transcribe(audio_path, word_timestamps=True)
        bloco, linhas, contador = [], [], 1

        for seg in segments:
            for palavra in seg.words:
                bloco.append(palavra)
                if len(bloco) == palavras_por_bloco:
                    ini = formatar_tempo(bloco[0].start)
                    fim = formatar_tempo(bloco[-1].end)
                    texto = " ".join(w.word for w in bloco)
                    linhas.append(f"{contador}\n{ini} --> {fim}\n{texto}\n")
                    contador += 1
                    bloco = []

        if bloco:
            ini = formatar_tempo(bloco[0].start)
            fim = formatar_tempo(bloco[-1].end)
            texto = " ".join(w.word for w in bloco)
            linhas.append(f"{contador}\n{ini} --> {fim}\n{texto}\n")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas))

        print("está no indice: ", i)
        cenas[i-1]["srt_path"] = srt_path
        logs.append(f"✅ Legenda {i} gerada com {palavras_por_bloco} palavras por bloco.")

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return logs
