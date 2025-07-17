"""Geração de narrações utilizando Selenium e ElevenLabs."""

import os
import json
import time
from modules.paths import get_paths
from modules.config import get_config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
path = get_paths()

def iniciar_driver():
    """Inicia o Chrome configurado para download automático dos áudios."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    #chrome_options.add_argument("--headless=new")  # Modo invisível
    chrome_options.add_argument("--disable-gpu")  # (opcional no Windows)
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": os.path.abspath(get_paths()["audios"]),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )
    return webdriver.Chrome(options=chrome_options)

def esperar(driver, selector, by=By.XPATH, clickable=False, timeout=20, seerroseguir=True):
    """Espera por um elemento visível ou clicável. Se `seerroseguir` for True, não lança erro se falhar."""
    wait = WebDriverWait(driver, timeout)
    cond = EC.element_to_be_clickable if clickable else EC.visibility_of_element_located
    try:
        return wait.until(cond((by, selector)))
    except:
        if seerroseguir:
            return None
        else:
            raise

def login(driver, voz="Brian"):
    """Realiza o login e seleciona a voz desejada no site da ElevenLabs."""

    driver.get("https://elevenlabs.io/app/speech-synthesis/text-to-speech")

    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(get_config("eleven_email"))
    driver.find_element(By.NAME, "password").send_keys(get_config("eleven_senha"))
    driver.find_element(By.NAME, "password").submit()

    time.sleep(3)
    driver.get("https://elevenlabs.io/app/speech-synthesis/text-to-speech")
    wait.until(EC.url_contains("/text-to-speech"))

    try:
        #print("Clicando em: Get started")
        esperar(driver, "//button[normalize-space()='Get started']", clickable=True, timeout=5, seerroseguir=True).click()
    except:
        pass

    #print("Clicando em: Select voice")
    esperar(driver, "//button[starts-with(@aria-label, 'Select voice')]", clickable=True, seerroseguir=True).click()

    #print(f"Escrevendo: {voz}")
    esperar(driver, '//input[@placeholder="Search voices..."]', seerroseguir=False).send_keys(voz)

    time.sleep(2)

    try:
        #print("verificando se tem voz escrita")
        nome_voz = esperar(driver, f'//p/span[contains(text(), "{voz}")]', timeout=5, seerroseguir=True).text.strip()
        if nome_voz.lower() != voz.lower():
            print(f"⚠️ Voz encontrada diferente: {nome_voz}")
    except:
        print(f"❌ Voz '{voz}' não encontrada")

    #print("selecionando voz")
    esperar(driver, f'//p/span[contains(text(), "{voz}")]', clickable=True, seerroseguir=True).click()

    #print("clicar no seletor de modelo")
    esperar(driver, "//button[starts-with(@aria-label, 'Select model')]", clickable=True, seerroseguir=True).click()
    #print("selecionando V2")
    esperar(driver, '//button[@value="eleven_multilingual_v2"]', clickable=True, seerroseguir=True).click()
    time.sleep(3)

def gerar_e_baixar(driver, texto, index):
    """Gera a narração no site e faz o download do arquivo gerado."""

    wait = WebDriverWait(driver, 20)

    textarea = esperar(driver, "//textarea")
    textarea.clear()
    textarea.send_keys(texto)

    esperar(driver, '//button[@aria-label="Generate speech Ctrl+Enter"]', clickable=True, seerroseguir=False).click()
    download_btn = esperar(driver, '//button[@aria-label="Download latest"]', clickable=True, seerroseguir=False)

    before = set(os.listdir(path["audios"]))
    download_btn.click()
    time.sleep(1)
    for _ in range(30):
        time.sleep(1)
        after = set(os.listdir(path["audios"]))
        new_files = after - before
        if new_files:
            break
    else:
        raise Exception("Download não detectado.")

    filename = new_files.pop()
    ext = os.path.splitext(filename)[1]
    src = os.path.join(path["audios"], filename)
    dst = os.path.join(path["audios"], f"narracao{index + 1}{ext}")
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)
    return dst

def run_gerar_narracoes(indices, voz="Brian", fonte="elevenlabs"):
    """Processa a geração de todas as narrações solicitadas."""

    with open(path["cenas"], encoding="utf-8") as f:
        cenas = json.load(f)

    logs = [f"🚀 Iniciando geração de narrações via {fonte}..."]

    if fonte == "elevenlabs":
        driver = iniciar_driver()
        try:
            login(driver, voz)
            for i in indices:
                texto = cenas[i].get("narracao")
                if not texto:
                    logs.append(f"⚠️ Cena {i+1} sem texto de narração.")
                    continue

                logs.append(f"🎙️ Gerando narração {i+1}: {texto[:30]}...")
                pathx = gerar_e_baixar(driver, texto, i)
                cenas[i]["audio_path"] = pathx
                logs.append(f"✅ Narração {i+1} salva em {pathx}")
        finally:
            driver.quit()

    elif fonte == "gemini":
        driver=iniciar_driver()
        try:
            for i in indices:
                texto=cenas[i].get("narracao")
                if not texto:
                    logs.append(f"⚠️ Cena {i + 1} sem texto.")
                    continue

                logs.append(f"🤖 Gerando via Gemini TTS: cena {i + 1}")
                pathx=gerar_com_gemini_selenium(driver, texto, i)
                cenas[i]["audio_path"]=pathx
                logs.append(f"✅ Gemini TTS: cena {i + 1} salva")
        finally:
            driver.quit()

    else:
        raise ValueError(f"Fonte de narração '{fonte}' não suportada.")

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return {"logs": logs, "cenas": cenas}

def gerar_com_gemini_selenium(driver, texto, index):
    """Gera narração no site TTS do Google Cloud (ou Gemini Studio) e baixa o áudio."""

    wait = WebDriverWait(driver, 20)

    driver.get("https://aistudio.google.com/generate-speech")

    time.sleep(500000)
    # Espera iframe da demo
    iframe = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='text-to-speech']")))
    driver.switch_to.frame(iframe)

    # Preenche o campo de texto
    textarea = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea")))
    textarea.clear()
    textarea.send_keys(texto)

    # Espera botão "Speak" ou "Download"
    speak_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Speak')]")))
    speak_btn.click()

    # Aguarda o botão "Download" aparecer
    download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download')]")))

    # Antes do clique, captura lista de arquivos existentes
    before = set(os.listdir(path["audios"]))
    download_btn.click()

    # Espera aparecer novo arquivo
    for _ in range(30):
        time.sleep(1)
        after = set(os.listdir(path["audios"]))
        new_files = after - before
        if new_files:
            break
    else:
        raise Exception("Download não detectado.")

    # Renomeia o arquivo para padronizar
    filename = new_files.pop()
    ext = os.path.splitext(filename)[1]
    src = os.path.join(path["audios"], filename)
    dst = os.path.join(path["audios"], f"narracao{index + 1}{ext}")
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)
    return dst