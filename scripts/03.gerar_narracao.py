import asyncio
import aiohttp
import json

API_KEY = "SUA_CHAVE_PIAPI"
BASE_URL = "https://api.piapi.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
ENTRADA_JSON = "cenas_com_videos.json"
SAIDA_JSON = "cenas_com_narracao.json"

# 🔁 Cria tarefa de narração
async def criar_audio(session, texto):
    payload = {
        "text": texto,
        "voice": "default"  # Se quiser uma voz específica, podemos ajustar
    }
    async with session.post(f"{BASE_URL}/tts/f5/create-task", json=payload) as resp:
        resp.raise_for_status()
        return await resp.json()

# 🔁 Checa até o áudio estar pronto
async def checar_audio(session, task_id):
    while True:
        await asyncio.sleep(5)
        async with session.get(f"{BASE_URL}/tts/f5/task/{task_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            if data["status"] == "completed":
                return data
            elif data["status"] == "failed":
                raise Exception(f"Narração {task_id} falhou.")
            print(f"Narração {task_id} ainda processando...")

# 🎯 Processa cada cena
async def processar_narracao(session, cena):
    texto = cena.get("narracao", "").strip()
    if not texto:
        return cena  # cena sem narração

    print(f"\n🔊 Gerando narração para texto: {texto}")
    criacao = await criar_audio(session, texto)
    task_id = criacao["task_id"]
    resultado = await checar_audio(session, task_id)

    cena["task_id_narracao"] = task_id
    cena["audio_narracao_url"] = resultado["audio_url"]
    print(f"✅ Narração pronta: {cena['audio_narracao_url']}")
    return cena

# 🔁 Loop principal
async def main():
    with open(ENTRADA_JSON, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tarefas = [processar_narracao(session, cena) for cena in cenas]
        resultados = await asyncio.gather(*tarefas)

    with open(SAIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Narrações geradas e salvas em {SAIDA_JSON}")

if __name__ == "__main__":
    asyncio.run(main())
