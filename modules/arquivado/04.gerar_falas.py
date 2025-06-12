import asyncio
import aiohttp
import json

API_KEY = "SUA_CHAVE_PIAPI"
BASE_URL = "https://api.piapi.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
ENTRADA_JSON = "cenas_com_narracao.json"
SAIDA_JSON = "cenas_com_falas.json"

# 🔁 Cria fala via TTS
async def criar_fala(session, texto, voz="default"):
    payload = {
        "text": texto,
        "voice": voz
    }
    async with session.post(f"{BASE_URL}/tts/f5/create-task", json=payload) as resp:
        resp.raise_for_status()
        return await resp.json()

# 🔁 Checa status da tarefa de fala
async def checar_fala(session, task_id):
    while True:
        await asyncio.sleep(5)
        async with session.get(f"{BASE_URL}/tts/f5/task/{task_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            if data["status"] == "completed":
                return data
            elif data["status"] == "failed":
                raise Exception(f"Fala {task_id} falhou.")
            print(f"Fala {task_id} ainda processando...")

# 🔁 Processa todas as falas de uma cena
async def processar_falas_da_cena(session, cena):
    falas = cena.get("falas", [])
    falas_com_audio = []

    for fala in falas:
        personagem = fala.get("personagem", "Narrador")
        texto = fala.get("texto", "")
        voz = fala.get("voz", "default")

        if not texto:
            continue

        print(f"\n🗣️ Gerando fala para {personagem}: \"{texto}\" [voz: {voz}]")
        criacao = await criar_fala(session, texto, voz)
        task_id = criacao["task_id"]
        resultado = await checar_fala(session, task_id)

        falas_com_audio.append({
            "personagem": personagem,
            "texto": texto,
            "voz": voz,
            "task_id_fala": task_id,
            "audio_fala_url": resultado["audio_url"]
        })

    cena["falas_com_audio"] = falas_com_audio
    return cena

# 🔁 Loop principal
async def main():
    with open(ENTRADA_JSON, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tarefas = [processar_falas_da_cena(session, cena) for cena in cenas]
        resultados = await asyncio.gather(*tarefas)

    with open(SAIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Todas as falas com áudio foram geradas e salvas em {SAIDA_JSON}")

if __name__ == "__main__":
    asyncio.run(main())
