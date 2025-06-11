import asyncio
import aiohttp
import json

API_KEY = "1014d470224d1bd03201a5e7c3641a8bfdfa5f3027451aca34b20de45d75bdc4"
BASE_URL = "https://api.piapi.ai"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

ENTRADA_JSON = "cenas_com_imagens.json"
SAIDA_JSON = "cenas_com_videos.json"

# 🔁 Cria vídeo com imagem + prompt usando modelo Hailuo
async def criar_video(session, image_url, prompt):
    payload = {
        "model": "hailuo",
        "task_type": "video_generation",
        "input": {
            "prompt": prompt,
            "model": "i2v-01",
            "image_url": image_url,
            "expand_prompt": True
        },
        "config": {
            "service_mode": "public",
            "webhook_config": {
                "endpoint": "",  # deixe vazio se não usar webhook
                "secret": ""
            }
        }
    }

    async with session.post(f"{BASE_URL}/api/v1/task", json=payload) as resp:
        resp.raise_for_status()
        data = await resp.json()
        print("🎥 Resposta ao criar vídeo:", data)
        return data

# 🔁 Checa até o vídeo estar pronto
async def checar_video(session, task_id):
    while True:
        await asyncio.sleep(10)
        async with session.get(f"{BASE_URL}/api/v1/task/{task_id}") as resp:
            resp.raise_for_status()
            data = await resp.json()
            status = data["data"]["status"]
            print(f"🔄 Status do vídeo {task_id}: {status}")
            if status == "completed":
                return data
            elif status == "failed":
                raise Exception(f"❌ Vídeo {task_id} falhou.")

# 🎯 Processa cada cena do JSON
async def processar_video(session, cena):
    prompt_animacao = cena.get("prompt_animacao", "").strip()
    image_url = cena.get("image_url", "").strip()

    if not prompt_animacao or not image_url:
        print("⚠️ Cena incompleta (sem imagem ou prompt de animação). Pulando...")
        return cena

    print(f"\n🎬 Criando vídeo para imagem: {image_url}")
    criacao = await criar_video(session, image_url, prompt_animacao)
    task_id = criacao["data"]["task_id"]
    resultado = await checar_video(session, task_id)

    cena["task_id_video"] = task_id
    cena["video_url"] = resultado["data"]["output"]["video_url"]
    print(f"✅ Vídeo pronto: {cena['video_url']}")
    return cena

# 🔁 Fluxo principal
async def main():
    with open(ENTRADA_JSON, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tarefas = [processar_video(session, cena) for cena in cenas]
        resultados = await asyncio.gather(*tarefas)

    with open(SAIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Todos os vídeos foram gerados e salvos em {SAIDA_JSON}")

if __name__ == "__main__":
    asyncio.run(main())
