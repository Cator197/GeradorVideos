import asyncio
import aiohttp
import json

API_KEY = "SUA_CHAVE_PIAPI"
BASE_URL = "https://api.piapi.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
ARQUIVO_ENTRADA = "cenas_com_efeitos.json"
ARQUIVO_SAIDA = "cenas_com_trilha.json"

# 🔁 Cria música via Udio/Suno com prompt de estilo
async def criar_trilha(session, prompt):
    payload = {
        "prompt": prompt
    }
    async with session.post(f"{BASE_URL}/udio/create-task", json=payload) as resp:
        resp.raise_for_status()
        return await resp.json()

# 🔁 Checa até a trilha estar pronta
async def checar_trilha(session, task_id):
    while True:
        await asyncio.sleep(10)
        async with session.get(f"{BASE_URL}/udio/task/{task_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            if data["status"] == "completed":
                return data
            elif data["status"] == "failed":
                raise Exception(f"Trilha sonora {task_id} falhou.")
            print(f"Trilha {task_id} ainda processando...")

# 🔁 Processa trilha sonora da cena
async def processar_trilha(session, cena):
    prompt = cena.get("trilha_sonora", "").strip()
    if not prompt:
        return cena

    print(f"\n🎵 Gerando trilha para: \"{prompt}\"")
    criacao = await criar_trilha(session, prompt)
    task_id = criacao["task_id"]
    resultado = await checar_trilha(session, task_id)

    cena["trilha_sonora_audio"] = {
        "descricao": prompt,
        "task_id": task_id,
        "audio_url": resultado["audio_url"]
    }
    print(f"✅ Trilha pronta: {resultado['audio_url']}")
    return cena

# 🔁 Loop principal
async def main():
    with open(ARQUIVO_ENTRADA, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tarefas = [processar_trilha(session, cena) for cena in cenas]
        resultados = await asyncio.gather(*tarefas)

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Trilhas sonoras geradas e salvas em {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    asyncio.run(main())
