import os
import aiohttp
import asyncio
import json

API_KEY = "1014d470224d1bd03201a5e7c3641a8bfdfa5f3027451aca34b20de45d75bdc4"
BASE_URL = "https://api.piapi.ai"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

ENTRADA_JSON = "cenas.json"
SAIDA_JSON = "cenas_com_imagens.json"
PASTA_IMAGENS = "imagens"

os.makedirs(PASTA_IMAGENS, exist_ok=True)

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
        await asyncio.sleep(10)
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

async def processar_cena(session, cena, index):
    prompt = cena["prompt_imagem"]
    print(f"🖼️ Gerando imagem {index + 1} para: {prompt}")
    criacao = await criar_imagem(session, prompt)
    task_id = criacao["data"]["task_id"]
    resultado = await checar_status(session, task_id)
    image_url = resultado["data"].get("output", {}).get("image_url")

    caminho_local = os.path.join(PASTA_IMAGENS, f"imagem{index + 1}.jpg")
    await baixar_imagem(session, image_url, caminho_local)

    cena["task_id_imagem"] = task_id
    cena["image_url"] = image_url
    cena["arquivo_local"] = caminho_local

    print(f"✅ Imagem {index + 1} salva em {caminho_local}")
    return cena

async def main():
    with open(ENTRADA_JSON, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tarefas = [processar_cena(session, cena, i) for i, cena in enumerate(cenas)]
        resultados = await asyncio.gather(*tarefas)

    with open(SAIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Todas as imagens foram geradas, URLs salvas em {SAIDA_JSON}, e arquivos em ./{PASTA_IMAGENS}/")

if __name__ == "__main__":
    asyncio.run(main())
