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
    base = get_config("pasta_salvar") or "."
    return {
        "base": base,
        "audios": os.path.join(base, "audios_narracoes"),
        "cenas": os.path.join(base, "cenas_com_imagens.json")
    }


def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(get_paths()["audios"]),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    return webdriver.Chrome(options=chrome_options)


def esperar(driver, selector, by=By.XPATH, clickable=False, timeout=20):
    wait = WebDriverWait(driver, timeout)
    cond = EC.element_to_be_clickable if clickable else EC.visibility_of_element_located
    return wait.until(cond((by, selector)))


def login(driver):
    driver.get("https://elevenlabs.io/app/speech-synthesis/text-to-speech")

    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(get_config("eleven_email"))
    driver.find_element(By.NAME, "password").send_keys(get_config("eleven_senha"))
    driver.find_element(By.NAME, "password").submit()

    wait.until(EC.url_contains("/text-to-speech"))

    try:
        print("Clicando em: Get started")
        esperar(driver, "//button[normalize-space()='Get started']", clickable=True, timeout=5).click()
    except:
        pass

    print("Clicando em: Select voice")
    esperar(driver, "//button[starts-with(@aria-label, 'Select voice')]", clickable=True).click()

    print("Escrevendo: Brian")
    esperar(driver, '//input[@placeholder="Search voices..."]').send_keys("Brian")

    time.sleep(2)

    try:
        print("verificando se tem Brian escrito")
        nome_voz = esperar(driver, '//p/span[contains(text(), "Brian")]', timeout=5).text.strip()
        if nome_voz.lower() != "brian":
            print(f"⚠️ Voz encontrada: {nome_voz}")
    except:
        print("❌ Voz 'Brian' não encontrada")

    print("selecionando Brian")
    esperar(driver, '//p/span[contains(text(), "Brian")]', clickable=True).click()
    print("clicar no seletor de modelo")
    esperar(driver, "//button[starts-with(@aria-label, 'Select model')]", clickable=True).click()
    print("selecioando V2")
    esperar(driver, '//button[@value="eleven_multilingual_v2"]', clickable=True).click()
    time.sleep(3)

def gerar_e_baixar(driver, texto, index):
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


def run_gerar_narracoes(indices):
    paths = get_paths()

    with open(paths["cenas"], encoding="utf-8") as f:
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

    with open(paths["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return {"logs": logs, "cenas": cenas}
