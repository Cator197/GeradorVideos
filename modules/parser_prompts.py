"""Parser de prompts para o gerador de vídeos.

Este módulo lê um arquivo de texto estruturado com os prompts de cada
cena e converte as informações em uma lista de dicionários. Quando
executado diretamente, gera um arquivo JSON a partir desse conteúdo.
"""

import json
import re

# Caminho padrão para o arquivo de texto com os prompts
ARQUIVO_TXT = "prompts.txt"
# Arquivo de saída utilizado ao executar este módulo como script
ARQUIVO_JSON = "cenas.json"

def parse_prompts_txt(caminho_txt):
    """Lê o arquivo de prompts em ``caminho_txt`` e devolve as cenas.

    Args:
        caminho_txt (str): Caminho para o arquivo ``.txt`` contendo os
            prompts.

    Returns:
        list[dict]: Lista de dicionários representando as cenas
            encontradas.
    """

    # Carrega todo o texto para memória
    with open(caminho_txt, "r", encoding="utf-8") as f:
        texto = f.read()

    # As cenas são separadas por '---'
    blocos = texto.split("---")
    cenas = []

    for bloco in blocos:
        # Estrutura que armazenará os dados de uma cena individual
        cena = {}

        # Extrai campos principais de cada bloco
        img = re.search(r"Imagem:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        anim = re.search(r"Animação:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        nar = re.search(r"Narração:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        trilha = re.search(r"Trilha Sonora:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)

        # Lista de efeitos sonoros associados à cena
        efeitos_raw = (
            re.findall(r"- ([\w_]+)", bloco.split("Efeitos Sonoros:")[-1])
            if "Efeitos Sonoros:" in bloco
            else []
        )

        # Falas com voz: personagem, texto e voz (opcional)
        falas_raw = re.findall(
            r"- Personagem:\s*(.+?)\s*Texto:\s*(.+?)\s*(?:Voz:\s*(.+?))?(?:\n|$)",
            bloco,
            re.DOTALL
        )
        falas = []
        # Converte tuplas em dicionários para facilitar o uso posterior
        for p, t, v in falas_raw:
            fala = {
                "personagem": p.strip(),
                "texto": t.strip(),
            }
            if v and v.strip():
                fala["voz"] = v.strip()
            falas.append(fala)

        # Adiciona as informações encontradas ao dicionário da cena
        if img:
            cena["prompt_imagem"] = img.group(1).strip()
        if anim:
            cena["prompt_animacao"] = anim.group(1).strip()
        if nar:
            cena["narracao"] = nar.group(1).strip()
        if falas:
            cena["falas"] = falas
        if efeitos_raw:
            cena["efeitos_sonoros"] = efeitos_raw
        if trilha:
            cena["trilha_sonora"] = trilha.group(1).strip()

        # Apenas blocos que possuem um prompt de imagem são considerados
        if "prompt_imagem" in cena:
            cenas.append(cena)

    # Devolve a lista de cenas extraídas
    return cenas

if __name__ == "__main__":
    # Executado diretamente, converte o arquivo texto em JSON
    cenas = parse_prompts_txt(ARQUIVO_TXT)

    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=4)

    print(f"✅ {len(cenas)} cenas salvas em {ARQUIVO_JSON}")
