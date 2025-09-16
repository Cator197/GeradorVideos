import os, json, re
from modules.config import get_config

# Diretório da pasta modules (onde está este arquivo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_RAIZ = os.path.dirname(BASE_DIR)

# Caminho para o .txt e saída padrão JSON
ARQUIVO_TXT = os.path.join(PASTA_RAIZ, "prompts.txt")
ARQUIVO_JSON = os.path.join(PASTA_RAIZ, "cenas.json")

def salvar_prompt_txt(conteudo, caminho=ARQUIVO_TXT):
    """Salva o conteúdo de prompts em um arquivo de texto.

    Parâmetros:
        conteudo (str): Texto completo contendo os prompts formatados.
        caminho (str): Caminho do arquivo que receberá o conteúdo.

    Retorna:
        None: O conteúdo é gravado diretamente no disco.
    """
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo.strip())

def parse_prompts_txt(caminho_txt=ARQUIVO_TXT):
    """Lê o arquivo de prompts e devolve a lista de cenas estruturadas.

    Parâmetros:
        caminho_txt (str): Caminho do arquivo ``prompts.txt`` a ser analisado.

    Retorna:
        list[dict]: Lista de cenas com prompts e metadados extraídos.
    """
    with open(caminho_txt, "r", encoding="utf-8") as f:
        texto = f.read()

    blocos = texto.split("---")
    cenas = []

    # Cada bloco representa uma cena descrita no arquivo
    for bloco in blocos:
        bloco=bloco.replace("image:", "imagem:")  # Faz a substituição antes da extração
        cena = {}
        img = re.search(r"Imagem:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        anim = re.search(r"Animação:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        nar = re.search(r"Narração:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)
        trilha = re.search(r"Trilha Sonora:\s*(.+?)(?:\n|$)", bloco, re.DOTALL)

        efeitos_raw = (
            re.findall(r"- ([\w_]+)", bloco.split("Efeitos Sonoros:")[-1])
            if "Efeitos Sonoros:" in bloco else []
        )

        falas_raw = re.findall(
            r"- Personagem:\s*(.+?)\s*Texto:\s*(.+?)\s*(?:Voz:\s*(.+?))?(?:\n|$)",
            bloco, re.DOTALL
        )
        falas = []
        for p, t, v in falas_raw:
            fala = {"personagem": p.strip(), "texto": t.strip()}
            if v and v.strip():
                fala["voz"] = v.strip()
            falas.append(fala)

        if img: cena["prompt_imagem"] = img.group(1).strip()
        if anim: cena["prompt_animacao"] = anim.group(1).strip()
        if nar: cena["narracao"] = nar.group(1).strip()
        if falas: cena["falas"] = falas
        if efeitos_raw: cena["efeitos_sonoros"] = efeitos_raw
        if trilha: cena["trilha_sonora"] = trilha.group(1).strip()

        if "prompt_imagem" in cena:
            cenas.append(cena)

    return cenas

def limpar_pastas_de_saida():
    """Remove arquivos temporários das pastas configuradas em ``pasta_salvar``.

    Parâmetros:
        Nenhum.

    Retorna:
        None: As pastas são limpas diretamente se existirem.
    """
    base = get_config("pasta_salvar") or os.getcwd()

    pastas = [
        os.path.join(base, "audios_narracoes"),
        os.path.join(base, "imagens"),
        os.path.join(base, "legendas_srt"),
        os.path.join(base, "videos_cenas")
    ]
    arquivo_json = os.path.join(os.getcwd(), "cenas_com_imagens.json")

    for pasta in pastas:
        if os.path.exists(pasta):
            # Remove todos os arquivos de cada pasta de saída
            for f in os.listdir(pasta):
                caminho = os.path.join(pasta, f)
                if os.path.isfile(caminho):
                    os.remove(caminho)

    if os.path.exists(arquivo_json):
        os.remove(arquivo_json)

if __name__ == "__main__":
    limpar_pastas_de_saida()
    cenas = parse_prompts_txt()

    # ✅ Copiar narração para legenda se ainda não existir
    for cena in cenas:
        if "narracao" in cena and "legenda" not in cena:
            cena["legenda"] = cena["narracao"]

    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=4)

    print(f"✅ {len(cenas)} cenas salvas em {ARQUIVO_JSON}")
