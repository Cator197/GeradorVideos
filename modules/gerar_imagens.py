import os
import json
import aiohttp
import asyncio
from modules.config import get_config

BASE_URL = "https://api.piapi.ai"

def get_paths():
    pasta_base = get_config("pasta_salvar") or os.getcwd()
    return {
        "pasta_base": pasta_base,
        "pasta_imagens": os.path.join(pasta_base, "imagens"),
        "entrada_json": os.path.join(os.getcwd(), "modules", "cenas.json"),
        "saida_json": os.path.join(pasta_base, "cenas_com_imagens.json")
    }

def get_headers():
    return {
        "x-api-key": get_config("api_key"),
        "Content-Type": "application/json"
    }

async def criar_imagem(session, prompt):
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
    async with session.get(url) as resp:
        resp.raise_for_status()
        with open(caminho_local, "wb") as f:
            f.write(await resp.read())

async def gerar_imagens_async(cenas, indices, logs):
    paths = get_paths()
    os.makedirs(paths["pasta_imagens"], exist_ok=True)

    async with aiohttp.ClientSession(headers=get_headers()) as session:
        for i in indices:
            prompt = cenas[i].get("prompt_imagem", "")

            logs.append(f"🎨 Gerando imagem {i+1}: {prompt[:50]}...")
            resp = await criar_imagem(session, prompt)
            task_id = resp["data"]["task_id"]
            logs.append(f"⏳ Aguardando conclusão da tarefa {task_id}...")
            resultado = await checar_status(session, task_id)
            url = resultado["data"].get("output", {}).get("image_url")
            caminho_local = os.path.join(paths["pasta_imagens"], f"imagem{i+1}.jpg")
            await baixar_imagem(session, url, caminho_local)
            cenas[i].update({
                "task_id_imagem": task_id,
                "image_url": url,
                "arquivo_local": caminho_local
            })


            logs.append(f"✅ Imagem {i+1} salva em {caminho_local}")
    return cenas

def run_gerar_imagens(indices):
    paths = get_paths()
    with open(paths["entrada_json"], encoding="utf-8") as f:
        cenas = json.load(f)

    logs = []
    cenas_atualizadas = asyncio.run(gerar_imagens_async(cenas, indices, logs))

    for i in indices:
        cenas[i] = cenas_atualizadas[i]

    with open(paths["saida_json"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=4)
        logs.append(f"✅ JSON atualizado salvo em {paths['saida_json']}")

    return {"cenas": cenas_atualizadas, "logs": logs}

def calcular_indices(scope, single, start, total):
    if scope == "all":
        return list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        return [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        return list(range(start - 1, total))
    else:
        raise ValueError("Parâmetros inválidos")

def gerar_eventos_para_stream(scope, single, start):
    import time

    paths = get_paths()
    with open(paths["entrada_json"], encoding="utf-8") as f:
        cenas = json.load(f)
    total = len(cenas)

    try:
        indices = calcular_indices(scope, single, start, total)
    except Exception:
        yield "data: ❌ Parâmetros inválidos\n\n"
        return

    logs = []

    async def executar():
        await gerar_imagens_async(cenas, indices, logs)

    asyncio.run(executar())

    with open(paths["saida_json"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    for log in logs:
        yield f"data: {log}\n\n"
        time.sleep(0.2)

    yield "data: 🔚 Geração de imagens finalizada\n\n"
