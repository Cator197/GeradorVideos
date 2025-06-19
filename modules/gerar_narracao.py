import os
import json
import time

from modules.config import get_config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Caminhos configuráveis
PASTA_BASE = get_config("pasta_salvar") or "."
PASTA_AUDIOS = os.path.join(PASTA_BASE, "audios_narracoes")
ARQUIVO_CENAS = os.path.join(PASTA_BASE, "cenas_com_imagens.json")
os.makedirs(PASTA_AUDIOS, exist_ok=True)

EMAIL = get_config("eleven_email")
PASSWORD = get_config("eleven_senha")

def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # Abre em tela cheia
    #chrome_options.add_argument("--headless=new")
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(PASTA_AUDIOS),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    return webdriver.Chrome(options=chrome_options)

def esperar_elemento(driver, xpath, timeout=20, clickable=False):
    wait = WebDriverWait(driver, timeout)
    cond = EC.element_to_be_clickable if clickable else EC.visibility_of_element_located
    return wait.until(cond((By.XPATH, xpath)))


def login(driver):
    # Abre a página de login do ElevenLabs
    driver.get("https://elevenlabs.io/app/speech-synthesis/text-to-speech")

    # Cria um objeto WebDriverWait para aguardar até 20 segundos pelos elementos
    wait=WebDriverWait(driver, 20)

    # Espera o campo de email estar visível e preenche com o EMAIL da conta
    wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(EMAIL)

    # Preenche o campo de senha
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)

    # Envia o formulário (pressiona ENTER no campo senha)
    driver.find_element(By.NAME, "password").submit()

    # Espera até que o URL da página contenha "/text-to-speech", confirmando que o login foi bem-sucedido
    wait.until(EC.url_contains("/text-to-speech"))

    # Tenta clicar no botão de confirmação de um possível pop-up (ex: aviso de cookies, confirmação etc.)
    try:
        esperar_elemento(driver, "/html/body/div[6]/div[2]/div[2]/button", timeout=5, clickable=True).click()
    except:
        # Se o botão não existir, ignora
        pass

    # Clica no botão "Add voice" para adicionar uma nova voz
    esperar_elemento(driver,"/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div/div[2]/div[1]/div/button",clickable=True).click()

    # Digita "Brian" no campo de busca de vozes
    esperar_elemento(driver,"/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div/div/div[1]/input").send_keys("Brian")
    time.sleep(2)
    #--------------------------
    xpath_brian="/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div/div/div[2]/div/div[1]/ul/li/div[2]/div[2]/div/div[1]/div[1]/p/span"

    try:
        elemento=WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, xpath_brian))
        )
        texto=elemento.text.strip()

        if texto.lower() == "brian":
            print("✅ O elemento contém o texto 'Brian'")
        else:
            print(f"⚠️ O texto encontrado foi: '{texto}'")
    except:
        print("❌ Elemento não encontrado")
    #-----------------------------------

    # Clica no item da lista correspondente à voz "Brian"
    esperar_elemento(driver,"/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div/div/div[2]/div/div[1]/ul/li/div[2]/div[2]/div/div[1]/div[1]/p",clickable=True).click()

    # Clica no botão para escolher a versão da voz Brian (ex: v1, v2, etc.)
    esperar_elemento(driver,"/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div/div[2]/div[2]/div/div/div/button",clickable=True).click()

    # Clica no botão "Confirm" para confirmar a seleção da voz
    esperar_elemento(driver,"/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div[2]/div[1]/button[2]",clickable=True ).click()


def gerar_e_baixar(driver, texto, index):
    wait = WebDriverWait(driver, 20)

    textarea = esperar_elemento(driver, "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/div/div[1]/textarea")
    textarea.clear()
    textarea.send_keys(texto)

    esperar_elemento(driver, "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/div/div[2]/div[2]/div/div[2]/div/button[2]", clickable=True).click()

    download_btn = esperar_elemento(driver, "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/div/div[2]/div[2]/div/div[2]/div/button[1]", clickable=True)
    before = set(os.listdir(PASTA_AUDIOS))
    download_btn.click()

    for _ in range(30):
        WebDriverWait(driver, 3).until(lambda d: set(os.listdir(PASTA_AUDIOS)) - before)
        after = set(os.listdir(PASTA_AUDIOS))
        new_files = after - before
        if new_files:
            break
    else:
        raise Exception("Download não ocorreu.")
    time.sleep(1)
    filename = new_files.pop()
    src = os.path.join(PASTA_AUDIOS, filename)
    ext = os.path.splitext(filename)[1]
    dst = os.path.join(PASTA_AUDIOS, f"narracao{index + 1}{ext}")
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)
    return dst

def run_gerar_narracoes(indices):
    with open(ARQUIVO_CENAS, encoding="utf-8") as f:
        cenas = json.load(f)

    logs = ["🚀 Iniciando geração de narrações..."]
    driver = iniciar_driver()
    try:
        login(driver)
        for i in indices:
            texto = cenas[i].get("narracao")
            if not texto:
                logs.append(f"⚠️ Cena {i+1} sem texto de narração.")
                continue

            logs.append(f"🎙️ Gerando narração {i+1}: {texto[:30]}...")
            path = gerar_e_baixar(driver, texto, i)
            cenas[i]["audio_path"] = path
            logs.append(f"✅ Narração {i+1} salva em {path}")
    finally:
        driver.quit()

    with open(ARQUIVO_CENAS, "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return {"logs": logs, "cenas": cenas}
