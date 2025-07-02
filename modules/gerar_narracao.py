"""Geração de narrações utilizando Selenium e ElevenLabs."""

import os
import json
import time

from modules.config import get_config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_paths():
    """Obtém os diretórios utilizados para salvar arquivos de áudio e cenas."""
    base = get_config("pasta_salvar") or os.getcwd()
    # Diretório da pasta modules (onde está este arquivo)
    BASE_DIR=os.path.dirname(os.path.abspath(__file__))
    ARQUIVO_JSON=os.path.join(BASE_DIR, "cenas.json")
    return {
        "base": base,
        "audios": os.path.join(base, "audios_narracoes"),
        "cenas": os.path.join(BASE_DIR, "cenas.json"),
    }


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


def esperar(driver, selector, by=By.XPATH, clickable=False, timeout=20):
    """Aguarda um elemento estar visível ou clicável."""
    wait = WebDriverWait(driver, timeout)
    cond = EC.element_to_be_clickable if clickable else EC.visibility_of_element_located
    return wait.until(cond((by, selector)))


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
        print("Clicando em: Get started")
        esperar(driver, "//button[normalize-space()='Get started']", clickable=True, timeout=5).click()
    except:
        pass

    print("Clicando em: Select voice")
    esperar(driver, "//button[starts-with(@aria-label, 'Select voice')]", clickable=True).click()

    print(f"Escrevendo: {voz}")
    esperar(driver, '//input[@placeholder="Search voices..."]').send_keys(voz)

    time.sleep(2)

    try:
        print("verificando se tem voz escrita")
        nome_voz = esperar(driver, f'//p/span[contains(text(), "{voz}")]', timeout=5).text.strip()
        if nome_voz.lower() != voz.lower():
            print(f"⚠️ Voz encontrada diferente: {nome_voz}")
    except:
        print(f"❌ Voz '{voz}' não encontrada")

    print("selecionando voz")
    esperar(driver, f'//p/span[contains(text(), "{voz}")]', clickable=True).click()

    print("clicar no seletor de modelo")
    esperar(driver, "//button[starts-with(@aria-label, 'Select model')]", clickable=True).click()
    print("selecionando V2")
    esperar(driver, '//button[@value="eleven_multilingual_v2"]', clickable=True).click()
    time.sleep(3)

def gerar_e_baixar(driver, texto, index):
    """Gera a narração no site e faz o download do arquivo gerado."""
    paths = get_paths()
    wait = WebDriverWait(driver, 20)

    textarea = esperar(driver, "//textarea")
    textarea.clear()
    textarea.send_keys(texto)

    esperar(driver, '//button[@aria-label="Generate speech Ctrl+Enter"]', clickable=True).click()
    download_btn = esperar(driver, '//button[@aria-label="Download latest"]', clickable=True)

    before = set(os.listdir(paths["audios"]))
    download_btn.click()
    time.sleep(1)
    for _ in range(30):
        time.sleep(1)
        after = set(os.listdir(paths["audios"]))
        new_files = after - before
        if new_files:
            break
    else:
        raise Exception("Download não detectado.")

    filename = new_files.pop()
    ext = os.path.splitext(filename)[1]
    src = os.path.join(paths["audios"], filename)
    dst = os.path.join(paths["audios"], f"narracao{index + 1}{ext}")
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)
    return dst


from modules.google_tts import gerar_google_audio  # ⬅️ no topo

def run_gerar_narracoes(indices, voz="Brian", fonte="elevenlabs"):
    """Processa a geração de todas as narrações solicitadas."""
    paths = get_paths()

    with open(paths["cenas"], encoding="utf-8") as f:
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
                path = gerar_e_baixar(driver, texto, i)
                cenas[i]["audio_path"] = path
                logs.append(f"✅ Narração {i+1} salva em {path}")
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
                path=gerar_com_gemini_selenium(driver, texto, i)
                cenas[i]["audio_path"]=path
                logs.append(f"✅ Gemini TTS: cena {i + 1} salva")
        finally:
            driver.quit()

    else:
        raise ValueError(f"Fonte de narração '{fonte}' não suportada.")

    with open(paths["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return {"logs": logs, "cenas": cenas}



def gerar_com_gemini_selenium(driver, texto, index):
    """Gera narração no site TTS do Google Cloud (ou Gemini Studio) e baixa o áudio."""
    paths = get_paths()
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
    before = set(os.listdir(paths["audios"]))
    download_btn.click()

    # Espera aparecer novo arquivo
    for _ in range(30):
        time.sleep(1)
        after = set(os.listdir(paths["audios"]))
        new_files = after - before
        if new_files:
            break
    else:
        raise Exception("Download não detectado.")

    # Renomeia o arquivo para padronizar
    filename = new_files.pop()
    ext = os.path.splitext(filename)[1]
    src = os.path.join(paths["audios"], filename)
    dst = os.path.join(paths["audios"], f"narracao{index + 1}{ext}")
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)
    return dst