import asyncio
import aiohttp
import json

API_KEY = "1014d470224d1bd03201a5e7c3641a8bfdfa5f3027451aca34b20de45d75bdc4"
BASE_URL = "https://api.piapi.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
ENTRADA_JSON = "cenas.json"
SAIDA_JSON = "cenas_com_imagens.json"

async def criar_imagem(session, prompt):
    async with session.post(f"{BASE_URL}/midjourney/imagine", json={"prompt": prompt}) as resp:
        resp.raise_for_status()
        return await resp.json()

async def checar_status(session, task_id):
    while True:
        await asyncio.sleep(10)
        async with session.get(f"{BASE_URL}/midjourney/task/{task_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            if data["status"] == "completed":
                return data
            elif data["status"] == "failed":
                raise Exception(f"Tarefa {task_id} falhou.")
            print(f"Tarefa {task_id} ainda processando...")

async def processar_cena(session, cena):
    prompt = cena["prompt_imagem"]
    print(f"🖼️ Gerando imagem para: {prompt}")
    criacao = await criar_imagem(session, prompt)
    task_id = criacao["task_id"]
    resultado = await checar_status(session, task_id)

    cena["task_id_imagem"] = task_id
    cena["image_url"] = resultado["image_url"]
    print(f"✅ Imagem pronta: {cena['image_url']}")
    return cena

async def main():
    with open(ENTRADA_JSON, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tarefas = [processar_cena(session, cena) for cena in cenas]
        resultados = await asyncio.gather(*tarefas)

    with open(SAIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Todas as imagens foram geradas e salvas em {SAIDA_JSON}")

if __name__ == "__main__":
    asyncio.run(main())
