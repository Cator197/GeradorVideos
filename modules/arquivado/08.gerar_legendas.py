import json

ARQUIVO_ENTRADA = "cenas_com_trilha.json"
ARQUIVO_SAIDA = "cenas_com_legendas.json"
VELOCIDADE_FALA = 13  # caracteres por segundo

def calcular_duracao(texto):
    return round(len(texto) / VELOCIDADE_FALA, 2)

def gerar_legendas(cena):
    legendas = []
    tempo_atual = 0.0

    # Narração (caso exista)
    if "narracao" in cena and cena["narracao"].strip():
        texto = cena["narracao"].strip()
        dur = calcular_duracao(texto)
        legendas.append({
            "texto": texto,
            "inicio": tempo_atual,
            "fim": round(tempo_atual + dur, 2)
        })
        tempo_atual += dur + 0.2  # pequeno espaço

    # Falas (caso existam)
    for fala in cena.get("falas", []):
        texto = fala["texto"]
        dur = calcular_duracao(texto)
        legendas.append({
            "texto": texto,
            "personagem": fala.get("personagem", ""),
            "inicio": tempo_atual,
            "fim": round(tempo_atual + dur, 2)
        })
        tempo_atual += dur + 0.2

    cena["legendas"] = legendas
    return cena

if __name__ == "__main__":
    with open(ARQUIVO_ENTRADA, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    cenas_com_legendas = [gerar_legendas(cena) for cena in cenas]

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(cenas_com_legendas, f, ensure_ascii=False, indent=4)

    print(f"✅ Legendas adicionadas e salvas em {ARQUIVO_SAIDA}")
