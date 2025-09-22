import os
import json
import re
import subprocess
from faster_whisper import WhisperModel
from modules.paths import get_paths

path = get_paths()

def formatar_tempo(segundos):
    """Converte segundos em HH:MM:SS,mmm."""
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos - int(segundos)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def carregar_modelo():
    """Carrega o modelo Whisper para transcrição."""
    return WhisperModel("small", device="cpu", compute_type="int8")

def gerar_srt_com_bloco(indices, palavras_por_bloco=4):
    """
    Gera SRTs por cena (indices base-0). Arquivos físicos são 1-based.
    """
    model = carregar_modelo()
    logs = []

    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    os.makedirs(path["legendas_srt"], exist_ok=True)

    for i in indices:
        if i < 0 or i >= len(cenas):
            logs.append(f"⚠️ Índice fora do intervalo: i={i} (len={len(cenas)}). Pulando.")
            continue

        file_id = i + 1
        audio_path = os.path.join(path["audios"], f"narracao{file_id}.mp3")
        srt_path   = os.path.join(path["legendas_srt"], f"legenda{file_id}.srt")

        if not os.path.exists(audio_path):
            logs.append(f"⚠️ Áudio não encontrado: narracao{file_id}.mp3.")
            continue

        try:
            segments, _ = model.transcribe(audio_path, word_timestamps=True)
        except Exception as exc:
            logs.append(f"❌ Falha ao transcrever narracao{file_id}.mp3: {exc}")
            continue

        bloco, linhas, contador = [], [], 1
        tem_palavras = False

        for seg in segments:
            if not hasattr(seg, "words") or seg.words is None:
                continue
            for palavra in seg.words:
                tem_palavras = True
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

        if not tem_palavras or not linhas:
            logs.append(f"⚠️ Sem palavras em narracao{file_id}.mp3. SRT não gerado.")
            continue

        try:
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(linhas))
        except OSError as exc:
            logs.append(f"❌ Falha ao salvar legenda{file_id}.srt: {exc}")
            continue

        cenas[i]["srt_path"] = srt_path
        logs.append(f"✅ Legenda {file_id} gerada com {palavras_por_bloco} palavras/bloco.")

    try:
        with open(path["cenas"], "w", encoding="utf-8") as f:
            json.dump(cenas, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logs.append(f"❌ Falha ao atualizar cenas.json: {exc}")

    return logs

def _tempo_para_segundos(valor: str) -> float:
    """Converte carimbo SRT (HH:MM:SS,mmm) em segundos."""
    try:
        horas, minutos, resto = valor.split(":")
        segundos, milissegundos = resto.split(",")
        return (
            int(horas) * 3600
            + int(minutos) * 60
            + int(segundos)
            + int(milissegundos) / 1000
        )
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Formato de tempo inválido: {valor}") from exc

def _duracao_audio_por_ffprobe(file_path: str) -> float:
    """
    Retorna a duração (em segundos) de um arquivo de áudio usando ffprobe.
    Requer ffmpeg/ffprobe disponível no PATH (já usado no app).
    """
    try:
        # -v error para suprimir logs; -show_entries format=duration -> só duração
        # -of default=noprint_wrappers=1:nokey=1 -> imprime apenas o número
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        dur = float(result.stdout.strip())
        # Segurança: normaliza negativos/NaN
        if not (dur > 0):
            return 0.0
        return dur
    except Exception:
        return 0.0

def _duracao_audio_por_id(file_id: int) -> float:
    """Atalho para pegar duração de narracao{file_id}.mp3."""
    audio_path = os.path.join(path["audios"], f"narracao{file_id}.mp3")
    if not os.path.exists(audio_path):
        return 0.0
    return _duracao_audio_por_ffprobe(audio_path)

def _maior_fim_local_de_srt(file_id: int) -> float:
    """
    Fallback: retorna o maior 'fim' (em segundos) presente em legenda{file_id}.srt.
    Útil se o áudio estiver ausente/ilegível.
    """
    srt_path = os.path.join(path["legendas_srt"], f"legenda{file_id}.srt")
    if not os.path.exists(srt_path):
        return 0.0

    try:
        with open(srt_path, "r", encoding="utf-8") as arquivo:
            conteudo = arquivo.read().lstrip("\ufeff").strip()
    except OSError:
        return 0.0

    if not conteudo:
        return 0.0

    maior = 0.0
    blocos = [b for b in re.split(r"\n\s*\n", conteudo) if b.strip()]
    for bloco in blocos:
        linhas = bloco.splitlines()
        if len(linhas) < 2:
            continue
        linha_tempo = linhas[1].strip()
        if "-->" not in linha_tempo:
            continue
        _, fim_str = [p.strip() for p in linha_tempo.split("-->")]
        try:
            fim_local = _tempo_para_segundos(fim_str)
            maior = max(maior, fim_local)
        except Exception:
            pass
    return maior

def unir_srt(indices, nome_arquivo="legendas_unidas.srt"):
    """
    Une SRTs (IDs 1-based) somando **duração real dos áudios** anteriores como deslocamento.
    Sem gap extra entre cenas. Se a duração do áudio não puder ser lida, faz fallback
    para o maior 'fim' local do SRT daquela cena.
    """
    logs = []

    if not indices:
        return {"logs": logs, "error": "Nenhum índice informado para união.", "status": 400}

    os.makedirs(path["legendas_srt"], exist_ok=True)

    entradas = []
    deslocamento = 0.0

    for pos, indice in enumerate(indices, start=1):
        srt_path = os.path.join(path["legendas_srt"], f"legenda{indice}.srt")

        # 1) Lê SRT atual (se existir) para extrair blocos
        if not os.path.exists(srt_path):
            logs.append(f"⚠️ Arquivo legenda{indice}.srt não encontrado. Pulando cena {indice}.")
            # Mesmo pulando a legenda, o deslocamento futuro deve considerar a duração do áudio desta cena?
            # Pela sua regra, o deslocamento é soma dos áudios anteriores — então se não há SRT, não adicionamos blocos,
            # porém, para cenas subsequentes, esta cena ainda "ocupa tempo" no timeline final do vídeo.
            # Portanto, ainda somamos a duração do áudio desta cena ao deslocamento.
            dur_audio = _duracao_audio_por_id(indice)
            if dur_audio > 0:
                deslocamento += dur_audio
                logs.append(f"ℹ️ Deslocamento +{dur_audio:.3f}s (duração do áudio {indice} sem SRT).")
            else:
                logs.append(f"ℹ️ Áudio {indice} ausente/ilegível; deslocamento inalterado.")
            continue

        try:
            with open(srt_path, "r", encoding="utf-8") as arquivo:
                conteudo = arquivo.read().lstrip("\ufeff").strip()
        except OSError as exc:
            logs.append(f"❌ Falha ao ler legenda{indice}.srt: {exc}")
            # Mesmo caso acima: ainda somamos a duração do áudio para manter timeline correta
            dur_audio = _duracao_audio_por_id(indice)
            if dur_audio > 0:
                deslocamento += dur_audio
                logs.append(f"ℹ️ Deslocamento +{dur_audio:.3f}s (duração do áudio {indice} mesmo sem SRT lido).")
            else:
                logs.append(f"ℹ️ Áudio {indice} ausente/ilegível; deslocamento inalterado.")
            continue

        if not conteudo:
            logs.append(f"⚠️ Arquivo legenda{indice}.srt vazio.")
            # Ainda assim, acumula duração do áudio para manter a linha do tempo
            dur_audio = _duracao_audio_por_id(indice)
            if dur_audio > 0:
                deslocamento += dur_audio
                logs.append(f"ℹ️ Deslocamento +{dur_audio:.3f}s (áudio {indice}).")
            else:
                logs.append(f"ℹ️ Áudio {indice} ausente/ilegível; deslocamento inalterado.")
            continue

        blocos = [bloco for bloco in re.split(r"\n\s*\n", conteudo) if bloco.strip()]
        blocos_validos = 0

        for bloco in blocos:
            linhas = bloco.splitlines()
            if len(linhas) < 2:
                continue

            linha_tempo = linhas[1].strip()
            if "-->" not in linha_tempo:
                logs.append(f"⚠️ Linha de tempo inválida ignorada na legenda {indice}: {linha_tempo}")
                continue

            inicio_str, fim_str = [p.strip() for p in linha_tempo.split("-->")]

            try:
                inicio_local = _tempo_para_segundos(inicio_str)
                fim_local = _tempo_para_segundos(fim_str)
            except ValueError as exc:
                logs.append(str(exc))
                continue

            if fim_local < inicio_local:
                logs.append(f"⚠️ Intervalo ignorado na legenda {indice}: fim antes do início.")
                continue

            texto = "\n".join(linhas[2:]) if len(linhas) > 2 else ""

            # Aplica deslocamento baseado em SOMA DAS DURAÇÕES DE ÁUDIO ANTERIORES
            inicio_global = inicio_local + deslocamento
            fim_global = fim_local + deslocamento

            entradas.append((inicio_global, fim_global, texto))
            blocos_validos += 1

        if blocos_validos == 0:
            logs.append(f"⚠️ Nenhum bloco válido em legenda{indice}.srt.")
        else:
            logs.append(f"🔗 Legenda {indice} adicionada com {blocos_validos} bloco(s) válido(s).")

        # 2) Atualiza deslocamento para a PRÓXIMA cena usando duração real do áudio atual
        dur_audio = _duracao_audio_por_id(indice)
        if dur_audio > 0:
            deslocamento += dur_audio
            logs.append(f"⏱️ Deslocamento acumulado: +{dur_audio:.3f}s (áudio {indice}) → total {deslocamento:.3f}s.")
        else:
            # Fallback: se não deu para medir o áudio, usa “maior fim” do SRT desta cena
            fim_local_max = _maior_fim_local_de_srt(indice)
            deslocamento += fim_local_max
            logs.append(
                f"⚠️ Áudio {indice} ausente/ilegível. Fallback deslocamento +{fim_local_max:.3f}s (maior fim do SRT). "
                f"Total {deslocamento:.3f}s."
            )

    if not entradas:
        return {"logs": logs, "error": "Nenhum SRT válido encontrado para união.", "status": 404}

    entradas.sort(key=lambda item: item[0])
    output_path = os.path.join(path["legendas_srt"], nome_arquivo)

    try:
        with open(output_path, "w", encoding="utf-8") as destino:
            for numero, (inicio, fim, texto) in enumerate(entradas, start=1):
                destino.write(f"{numero}\n{formatar_tempo(inicio)} --> {formatar_tempo(fim)}\n")
                if texto:
                    destino.write(f"{texto}\n")
                destino.write("\n")
    except OSError as exc:
        logs.append(f"❌ Falha ao salvar unificado: {exc}")
        return {"logs": logs, "error": "Falha ao salvar o SRT unificado.", "status": 500}

    logs.append(f"💾 Arquivo unificado salvo em: {output_path}")
    logs.append(f"✅ Total de {len(entradas)} bloco(s) combinados.")
    return {"logs": logs, "output": output_path, "message": f"Legendas unidas com sucesso em: {output_path}"}
