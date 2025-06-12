import json
import os

ARQUIVO_JSON = "cenas_com_legendas.json"
PASTA_SAIDA = "legendas_srt"

def segundos_para_srt(seg):
    h = int(seg // 3600)
    m = int((seg % 3600) // 60)
    s = int(seg % 60)
    ms = int(round((seg - int(seg)) * 1000))
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def salvar_legenda_srt(cena, indice):
    legendas = cena.get("legendas", [])
    if not legendas:
        return

    nome_arquivo = os.path.join(PASTA_SAIDA, f"legenda_cena_{indice+1}.srt")
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        for i, bloco in enumerate(legendas, start=1):
            f.write(f"{i}\n")
            f.write(f"{segundos_para_srt(bloco['inicio'])} --> {segundos_para_srt(bloco['fim'])}\n")
            f.write(f"{bloco['texto']}\n\n")

def gerar_legendas_srt():
    if not os.path.exists(PASTA_SAIDA):
        os.makedirs(PASTA_SAIDA)

    with open(ARQUIVO_JSON, "r", encoding="utf-8") as f:
        cenas = json.load(f)

    for i, cena in enumerate(cenas):
        salvar_legenda_srt(cena, i)

    print(f"✅ Arquivos .srt salvos em: {PASTA_SAIDA}/")

if __name__ == "__main__":
    gerar_legendas_srt()
