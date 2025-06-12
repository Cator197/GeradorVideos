import asyncio
import aiohttp
import json

API_KEY = "1014d470224d1bd03201a5e7c3641a8bfdfa5f3027451aca34b20de45d75bdc4"
BASE_URL = "https://api.piapi.ai"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

ENTRADA_JSON = "cenas_com_videos.json"
SAIDA_JSON = "cenas_com_narracao.json"

# 🔁 Cria tarefa de narração (zero-shot TTS)
async def criar_audio(session, texto):
    payload = {
        "model": "Qubico/tts",
        "task_type": "zero-shot",
        "input": {
            "gen_text": texto,
            "ref_audio": "",   # Pode adicionar referência de voz se quiser imitar
            "ref_text": ""
        },
        "config": {
            "service_mode": "public",
            "webhook_config": {
                "endpoint": "",
                "secret": ""
            }
        }
    }

    async with session.post(f"{BASE_URL}/api/v1/task", json=payload) as resp:
        resp.raise_for_status()
        data = await resp.json()
        print("🔊 Resposta ao criar áudio:", data)
        return data

# 🔁 Checa até o áudio estar pronto
async def checar_audio(session, task_id):
    while True:
        await asyncio.sleep(5)
        async with session.get(f"{BASE_URL}/api/v1/task/{task_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            status = data["data"]["status"]
            print(f"⏳ Status da narração {task_id}: {status}")
            if status == "completed":
                return data
            elif status == "failed":
                raise Exception(f"Narração {task_id} falhou.")

# 🎯 Processa cada cena
async def processar_narracao(session, cena):
    texto = cena.get("narracao", "").strip()
    if not texto:
        print("⚠️ Cena sem texto para narração. Pulando...")
        return cena

    print(f"\n🎤 Gerando narração para: {texto}")
    criacao = await criar_audio(session, texto)
    task_id = criacao["data"]["task_id"]
    resultado = await checar_audio(session, task_id)

    cena["task_id_narracao"] = task_id
    cena["audio_narracao_url"] = resultado["data"]["output"]["audio_url"]
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
