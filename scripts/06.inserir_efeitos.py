import json
import os

ARQUIVO_ENTRADA = "cenas_com_lipsync.json"
ARQUIVO_SAIDA = "cenas_com_efeitos.json"
PASTA_EFEITOS = "efeitos_sonoros"  # Pasta local com os arquivos

def aplicar_efeitos_sonoros(cenas):
    for cena in cenas:
        efeitos = cena.get("efeitos_sonoros", [])
        efeitos_aplicados = []

        for efeito in efeitos:
            nome_arquivo = f"{efeito}.mp3"
            caminho_completo = os.path.join(PASTA_EFEITOS, nome_arquivo)

            if os.path.exists(caminho_completo):
                efeitos_aplicados.append({
                    "nome": efeito,
                    "arquivo": caminho_completo
                })
            else:
                print(f"⚠️ Efeito '{efeito}' não encontrado em {PASTA_EFEITOS}")

        cena["efeitos_aplicados"] = efeitos_aplicados

    return cenas

if __name__ == "__main__":
    with open(ARQUIVO_ENTRADA, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    cenas_com_efeitos = aplicar_efeitos_sonoros(cenas)

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(cenas_com_efeitos, f, ensure_ascii=False, indent=4)

    print(f"✅ Efeitos aplicados e salvos em {ARQUIVO_SAIDA}")
