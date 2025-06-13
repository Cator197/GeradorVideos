import os
import json
import aiohttp
import asyncio

# ——— Configurações de API e caminhos ———
API_KEY     = "1014d470224d1bd03201a5e7c3641a8bfdfa5f3027451aca34b20de45d75bdc4"  # sua chave aqui
BASE_URL    = "https://api.piapi.ai"
HEADERS     = {"x-api-key": API_KEY, "Content-Type": "application/json"}

MODULE_DIR    = os.path.dirname(__file__)
ENTRADA_JSON  = os.path.join(MODULE_DIR, "cenas.json")
SAIDA_JSON    = os.path.join(MODULE_DIR, "cenas_com_imagens.json")
PASTA_IMAGENS = os.path.join(MODULE_DIR, "imagens")
os.makedirs(PASTA_IMAGENS, exist_ok=True)

# ——— Funções internas (async) ———
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

# ——— Processo completo com logging ———
async def _gerar(cenas, indices, logs):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for i in indices:
            prompt = cenas[i].get("prompt_imagem", "")
            print(f"🎨 Gerando imagem {i+1}: {prompt[:50]}...")
            logs.append(f"🎨 Gerando imagem {i+1}: {prompt[:50]}...")
            # 1) cria tarefa
            resp = await criar_imagem(session, prompt)
            task_id = resp["data"]["task_id"]
            print(f"⏳ Aguardando conclusão da tarefa {task_id}...")
            logs.append(f"⏳ Aguardando conclusão da tarefa {task_id}...")
            # 2) espera terminar
            resultado = await checar_status(session, task_id)
            url = resultado["data"].get("output", {}).get("image_url")
            # 3) baixa
            filename = f"imagem{i+1}.jpg"
            caminho_local = os.path.join(PASTA_IMAGENS, filename)
            await baixar_imagem(session, url, caminho_local)
            # 4) atualiza cena e log
            cenas[i].update({
                "task_id_imagem": task_id,
                "image_url": url,
                "arquivo_local": caminho_local
            })
            print(f"✅ Imagem {i+1} salva em {caminho_local}")
            logs.append(f"✅ Imagem {i+1} salva em {caminho_local}")
    return cenas

# ——— Função síncrona para o Flask chamar ———
def run_gerar_imagens(indices):
    # 1) carrega cenas
    with open(ENTRADA_JSON, encoding="utf-8") as f:
        cenas = json.load(f)
    # 2) gera imagens + logs
    logs = []
    cenas_atualizadas = asyncio.run(_gerar(cenas, indices, logs))
    # 3) salva JSON de saída
    with open(SAIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(cenas_atualizadas, f, ensure_ascii=False, indent=4)
    # 4) retorna dados para o front
    return {
        "cenas": cenas_atualizadas,
        "logs": logs
    }

# Quando executado diretamente, avisa para usar via Flask
if __name__ == "__main__":
    print("Este módulo deve ser chamado pelo Flask via run_gerar_imagens(indices).")
