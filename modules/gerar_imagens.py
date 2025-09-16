"""Geração de imagens a partir de prompts utilizando a API PIAPI.AI."""

import os
import json
import aiohttp
import asyncio
from modules.config import get_config
from modules.paths import get_paths
from modules.licenca import get_creditos, debitar_creditos, get_api_key

paths = get_paths()

BASE_URL = "https://api.piapi.ai"

def get_headers():
    """Monta os cabeçalhos necessários para autenticar na API de imagens.

    Parâmetros:
        Nenhum.

    Retorna:
        dict: Cabeçalhos HTTP contendo a chave da API e o tipo de conteúdo.
    """
    return {
        "x-api-key": get_api_key(),
        "Content-Type": "application/json"
    }

async def criar_imagem(session, prompt):
    """Envia a requisição de criação de imagem e retorna o identificador da tarefa.

    Parâmetros:
        session (aiohttp.ClientSession): Sessão HTTP compartilhada entre as requisições.
        prompt (str): Texto descrevendo o conteúdo visual desejado.

    Retorna:
        dict: Resposta JSON contendo os dados da tarefa criada.
    """
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
    """Verifica periodicamente o status de uma tarefa até sua conclusão.

    Parâmetros:
        session (aiohttp.ClientSession): Sessão HTTP utilizada para a consulta.
        task_id (str): Identificador retornado pela API para a tarefa.

    Retorna:
        dict: Dados completos da tarefa concluída.
    """
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
    """Baixa a imagem gerada e salva no caminho informado.

    Parâmetros:
        session (aiohttp.ClientSession): Sessão HTTP responsável pelo download.
        url (str): URL da imagem disponibilizada pela API.
        caminho_local (str): Caminho completo onde a imagem será persistida.

    Retorna:
        None: O arquivo é gravado diretamente no sistema de arquivos.
    """
    async with session.get(url) as resp:
        resp.raise_for_status()
        with open(caminho_local, "wb") as f:
            f.write(await resp.read())

async def processar_cena(session, i, cenas, logs, paths):
    """Gera e salva a imagem correspondente a uma cena específica.

    Parâmetros:
        session (aiohttp.ClientSession): Sessão HTTP utilizada para a API.
        i (int): Índice da cena a ser processada.
        cenas (list[dict]): Lista com os dados de todas as cenas.
        logs (list[str]): Lista mutável usada para registrar o andamento.
        paths (dict): Caminhos configurados para armazenamento local.

    Retorna:
        None: Os dados da cena e os logs são atualizados in place.
    """
    if get_creditos() < 10:
        logs.append(f"❌ Créditos insuficientes para gerar imagem {i + 1}.")
        return
    try:
        prompt = cenas[i].get("prompt_imagem", "")
        logs.append(f"🎨 Gerando imagem {i+1}: {prompt[:50]}...")
        resp = await criar_imagem(session, prompt)
        task_id = resp["data"]["task_id"]
        logs.append(f"⏳ Aguardando conclusão da tarefa {task_id}...")
        resultado = await checar_status(session, task_id)
        url = resultado["data"].get("output", {}).get("image_url")
        caminho_local = os.path.join(paths["imagens"], f"imagem{i+1}.jpg")
        await baixar_imagem(session, url, caminho_local)
        cenas[i].update({
            "task_id_imagem": task_id,
            "image_url": url,
            "arquivo_local": caminho_local
        })
        logs.append(f"✅ Imagem {i+1} salva em {caminho_local}")
        debitar_creditos(10)
        logs.append(f"💳 10 créditos debitados com sucesso.")
    except Exception as e:
        logs.append(f"❌ Erro ao gerar imagem {i+1}: {e}")

async def gerar_imagens_async(cenas, indices, logs):
    """Orquestra a geração de imagens de forma assíncrona.

    Parâmetros:
        cenas (list[dict]): Lista completa das cenas carregadas do arquivo.
        indices (Iterable[int]): Índices das cenas que devem ser geradas.
        logs (list[str]): Estrutura compartilhada para registrar mensagens.

    Retorna:
        list[dict]: Lista de cenas atualizadas após a geração.
    """

    os.makedirs(paths["imagens"], exist_ok=True)

    async with aiohttp.ClientSession(headers=get_headers()) as session:
        tarefas = [
            processar_cena(session, i, cenas, logs, paths)
            for i in indices
        ]
        await asyncio.gather(*tarefas)

    return cenas

def run_gerar_imagens(indices):
    """Executa a geração de imagens para os índices solicitados.

    Parâmetros:
        indices (Iterable[int]): Conjunto de cenas selecionadas pelo usuário.

    Retorna:
        dict: Estrutura contendo as cenas atualizadas e o histórico de logs.
    """
    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    logs = []

    logs=excluir_arquivos(indices)

    # ✅ Gerar as novas imagens
    cenas_atualizadas = asyncio.run(gerar_imagens_async(cenas, indices, logs))

    for i in indices:
        cenas[i] = cenas_atualizadas[i]
        if "legenda" not in cenas[i] and "narracao" in cenas[i]:
            cenas[i]["legenda"] = cenas[i]["narracao"]

    with open(paths["cenas_com_imagens"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=4)
        logs.append(f"✅ JSON atualizado salvo em {paths['cenas_com_imagens']}")

    return {"cenas": cenas_atualizadas, "logs": logs}

def calcular_indices(scope, single, start, total, selected=None):
    """Calcula os índices das cenas com base nos filtros escolhidos.

    Parâmetros:
        scope (str): Escopo selecionado (all, single, from ou selected).
        single (int | None): Índice único informado pelo usuário.
        start (int | None): Posição inicial quando o escopo é ``from``.
        total (int): Quantidade total de cenas disponíveis.
        selected (str | None): Lista textual de índices separados por vírgula.

    Retorna:
        list[int]: Lista de índices válidos conforme a escolha do usuário.
    """
    if scope == "all":
        return list(range(total))
    elif scope == "single" and single and 1 <= single <= total:
        return [single - 1]
    elif scope == "from" and start and 1 <= start <= total:
        return list(range(start - 1, total))
    elif scope == "selected":
        if not selected:
            raise ValueError("Nenhum índice selecionado.")
        indices=[int(x.strip()) - 1 for x in selected.split(",") if x.strip().isdigit()]
        return [i for i in indices if 0 <= i < total]
    else:
        raise ValueError("Parâmetros inválidos")

def gerar_eventos_para_stream(scope, single, start, selected=None):
    """Gera eventos de texto para acompanhar o progresso via SSE.

    Parâmetros:
        scope (str): Estratégia de seleção das cenas.
        single (int | None): Índice único solicitado pelo usuário.
        start (int | None): Ponto inicial para processamentos sequenciais.
        selected (str | None): Lista textual de índices específicos.

    Retorna:
        Generator[str, None, None]: Mensagens formatadas para o stream.
    """
    import time


    with open(paths["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)
    total = len(cenas)

    try:
        indices = calcular_indices(scope, single, start, total, selected)
        logs=excluir_arquivos(indices)
    except Exception as e:
        yield f"data: ❌ Erro ao calcular índices: {str(e)}\n\n"
        return

    logs = []

    async def executar():
        await gerar_imagens_async(cenas, indices, logs)

    asyncio.run(executar())

    with open(paths["cenas_com_imagens"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    for log in logs:
        yield f"data: {log}\n\n"
        time.sleep(0.2)

    yield "data: 🔚 Geração de imagens finalizada\n\n"

def excluir_arquivos(indices):
    """Remove arquivos antigos de imagens associados aos índices informados.

    Parâmetros:
        indices (Iterable[int]): Conjunto de cenas que serão regeneradas.

    Retorna:
        list[str]: Mensagens com o resultado da remoção de cada arquivo.
    """
    logs = []
    for i in indices:
        nome_base = f"imagem{i+1}"
        for ext in [".jpg", ".png", ".mp4"]:
            caminho = os.path.join(paths["imagens"], nome_base + ext)
            if os.path.exists(caminho):
                try:
                    os.remove(caminho)
                    logs.append(f"🗑️ Apagado: {caminho}")
                except Exception as e:
                    logs.append(f"⚠️ Erro ao apagar {caminho}: {e}")
    return logs
