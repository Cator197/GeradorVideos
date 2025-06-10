import json
import re

ARQUIVO_TXT = "prompts.txt"
ARQUIVO_JSON = "cenas.json"

def parse_prompts_txt(caminho_txt):
    with open(caminho_txt, "r", encoding="utf-8") as f:
        texto = f.read()

    blocos = texto.split("---")
    cenas = []

    for bloco in blocos:
        cena = {}

        # Extrai campos principais
        img = re.search(r"Imagem:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        anim = re.search(r"Animação:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        nar = re.search(r"Narração:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        trilha = re.search(r"Trilha Sonora:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)

        # Efeitos sonoros
        efeitos_raw = re.findall(r"- ([\w_]+)", bloco.split("Efeitos Sonoros:")[-1]) if "Efeitos Sonoros:" in bloco else []

        # Falas com Voz (Personagem, Texto, Voz)
        falas_raw = re.findall(
            r"- Personagem:\s*(.+?)\s*Texto:\s*(.+?)\s*(?:Voz:\s*(.+?))?(?:\n|$)",
            bloco,
            re.DOTALL
        )
        falas = []
        for p, t, v in falas_raw:
            fala = {
                "personagem": p.strip(),
                "texto": t.strip()
            }
            if v and v.strip():
                fala["voz"] = v.strip()
            falas.append(fala)

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

        if "prompt_imagem" in cena:
            cenas.append(cena)

    return cenas

if __name__ == "__main__":
    cenas = parse_prompts_txt(ARQUIVO_TXT)

    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=4)

    print(f"✅ {len(cenas)} cenas salvas em {ARQUIVO_JSON}")
