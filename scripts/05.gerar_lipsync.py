import asyncio
import aiohttp
import json

API_KEY = "SUA_CHAVE_PIAPI"
BASE_URL = "https://api.piapi.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
ENTRADA_JSON = "cenas_com_falas.json"
SAIDA_JSON = "cenas_com_lipsync.json"

# 🔁 Cria lipsync com imagem + áudio
async def criar_lipsync(session, image_url, audio_url):
    payload = {
        "image_url": image_url,
        "audio_url": audio_url
    }
    async with session.post(f"{BASE_URL}/kling/lipsync/create-task", json=payload) as resp:
        resp.raise_for_status()
        return await resp.json()

# 🔁 Checa status da tarefa de lipsync
async def checar_lipsync(session, task_id):
    while True:
        await asyncio.sleep(10)
        async with session.get(f"{BASE_URL}/kling/task/{task_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            if data["status"] == "completed":
                return data
            elif data["status"] == "failed":
                raise Exception(f"Lipsync {task_id} falhou.")
            print(f"Lipsync {task_id} ainda processando...")

# 🔁 Processa lipsync de cada fala
async def processar_lipsyncs_da_cena(session, cena):
    image_url = cena.get("image_url", "")
    falas_com_audio = cena.get("falas_com_audio", [])

    lipsyncs = []

    for fala in falas_com_audio:
        personagem = fala["personagem"]
        audio_url = fala["audio_fala_url"]

        print(f"\n🎤 Lipsync para {personagem} com áudio: {audio_url}")
        criacao = await criar_lipsync(session, image_url, audio_url)
        task_id = criacao["task_id"]
        resultado = await checar_lipsync(session, task_id)

        lipsyncs.append({
            "personagem": personagem,
            "audio_fala_url": audio_url,
            "task_id_lipsync": task_id,
            "video_lipsync_url": resultado["video_url"]
        })

    cena["lipsyncs"] = lipsyncs
    return cena

# 🔁 Loop principal
async def main():
    with open(ENTRADA_JSON, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tarefas = [processar_lipsyncs_da_cena(session, cena) for cena in cenas]
        resultados = await asyncio.gather(*tarefas)

    with open(SAIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Todos os vídeos com lipsync foram salvos em {SAIDA_JSON}")

if __name__ == "__main__":
    asyncio.run(main())
