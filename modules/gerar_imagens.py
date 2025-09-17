"""Geração de imagens a partir de prompts utilizando a API PIAPI.AI."""

import os
import json
import aiohttp
import asyncio
from modules.paths import get_paths
from modules.licenca import get_creditos, debitar_creditos, get_api_key


BASE_URL = "https://api.piapi.ai"

def get_headers():
    return {
        "x-api-key": get_api_key(),
        "Content-Type": "application/json"
    }

async def criar_imagem(session, prompt):
    """Envia a requisição de criação da imagem e retorna o JSON da task."""
    payload = {
        "model": "Qubico/flux1-schnell",
        "task_type": "txt2img",
        "input": {
            "prompt": prompt,
            "width": 576,
            "height": 1024,
            "process_mode": "turbo",
            "skip_prompt_check": False
        }
    }
    async with session.post(f"{BASE_URL}/api/v1/task", json=payload) as resp:
        resp.raise_for_status()
        return await resp.json()

async def checar_status(session, task_id):
    """Verifica periodicamente o status da tarefa de geração."""
    while True:
        await asyncio.sleep(5)
        async with session.get(f"{BASE_URL}/api/v1/task/{task_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            status = data["data"]["status"]
            if status == "completed":
                return data
            elif status == "failed":
                raise Exception(f"Tarefa {task_id} falhou.")

async def baixar_imagem(session, url, caminho_local):
    """Realiza o download da imagem gerada para o caminho informado."""
    async with session.get(url) as resp:
        resp.raise_for_status()
        with open(caminho_local, "wb") as f:
            f.write(await resp.read())

async def processar_cena(session, i, cenas, logs):
    """Processa individualmente uma cena para gerar a imagem."""
    paths=get_paths()
    if get_creditos() < 10:
        logs.append(f"❌ Créditos insuficientes para gerar imagem {i + 1}.")
        return
    try:
        prompt = cenas[i].get("prompt_imagem", "")
        logs.append(f"🎨 Gerando imagem {i+1}: {prompt[:50]}...")
        resp = await criar_imagem(session, prompt)
        task_id = resp["data"]["task_id"]
        logs.append(f"⏳ Aguardando conclusão da tarefa {task_id}...")
        resultado = await checar_status(session, task_id)
        url = resultado["data"].get("output", {}).get("image_url")
        caminho_local = os.path.join(paths["imagens"], f"imagem{i+1}.jpg")
        await baixar_imagem(session, url, caminho_local)
        cenas[i].update({
            "task_id_imagem": task_id,
            "image_url": url,
            "arquivo_local": caminho_local
        })
        logs.append(f"✅ Imagem {i+1} salva em {caminho_local}")
        debitar_creditos(10)
        logs.append(f"💳 10 créditos debitados com sucesso.")
    except Exception as e:
        logs.append(f"❌ Erro ao gerar imagem {i+1}: {e}")

async def gerar_imagens_async(cenas, indices, logs):
    """Processa a geração das imagens de forma paralela."""
    paths=get_paths()
    os.makedirs(paths["imagens"], exist_ok=True)

    async with aiohttp.ClientSession(headers=get_headers()) as session:
        tarefas = [
            processar_cena(session, i, cenas, logs)
            for i in indices
        ]
        await asyncio.gather(*tarefas)

    return cenas

def run_gerar_imagens(indices):
    paths=get_paths()
    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    logs = []

    logs=excluir_arquivos(indices)

    # ✅ Gerar as novas imagens
    cenas_atualizadas = asyncio.run(gerar_imagens_async(cenas, indices, logs))

    for i in indices:
        cenas[i] = cenas_atualizadas[i]
        if "legenda" not in cenas[i] and "narracao" in cenas[i]:
            cenas[i]["legenda"] = cenas[i]["narracao"]

    with open(paths["cenas_com_imagens"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=4)
        logs.append(f"✅ JSON atualizado salvo em {paths['cenas_com_imagens']}")

    return {"cenas": cenas_atualizadas, "logs": logs}

def calcular_indices(scope, single, start, total, selected=None):
    """Calcula os índices das cenas com base nos parâmetros da interface."""
    if scope == "all":
        return list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        return [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        return list(range(start - 1, total))
    elif scope == "selected":
        if not selected:
            raise ValueError("Nenhum índice selecionado.")
        indices=[int(x.strip()) - 1 for x in selected.split(",") if x.strip().isdigit()]
        return [i for i in indices if 0 <= i < total]
    else:
        raise ValueError("Parâmetros inválidos")

def gerar_eventos_para_stream(scope, single, start, selected=None):
    import time

    paths=get_paths()
    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)
    total = len(cenas)

    try:
        indices = calcular_indices(scope, single, start, total, selected)
        logs=excluir_arquivos(indices)
    except Exception as e:
        yield f"data: ❌ Erro ao calcular índices: {str(e)}\n\n"
        return

    logs = []

    async def executar():
        await gerar_imagens_async(cenas, indices, logs)

    asyncio.run(executar())

    with open(paths["cenas_com_imagens"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    for log in logs:
        yield f"data: {log}\n\n"
        time.sleep(0.2)

    yield "data: 🔚 Geração de imagens finalizada\n\n"

def excluir_arquivos(indices):
    paths=get_paths()
    logs = []
    for i in indices:
        nome_base = f"imagem{i+1}"
        for ext in [".jpg", ".png", ".mp4"]:
            caminho = os.path.join(paths["imagens"], nome_base + ext)
            if os.path.exists(caminho):
                try:
                    os.remove(caminho)
                    logs.append(f"🗑️ Apagado: {caminho}")
                except Exception as e:
                    logs.append(f"⚠️ Erro ao apagar {caminho}: {e}")
    return logs
