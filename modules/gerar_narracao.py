import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ARQUIVO_CENAS = os.path.join(os.path.dirname(__file__), "cenas_com_imagens.json")
PASTA_AUDIOS = os.path.join(os.path.dirname(__file__), "audios_narracoes")
os.makedirs(PASTA_AUDIOS, exist_ok=True)

EMAIL = "cdgproducoes2@gmail.com"
PASSWORD = "@Producoes147856#2"

def iniciar_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(PASTA_AUDIOS),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    return webdriver.Chrome(options=chrome_options)

def login(driver):
    driver.get("https://elevenlabs.io/app/speech-synthesis/text-to-speech")
    wait = WebDriverWait(driver, 20)
    wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(EMAIL)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD)
    driver.find_element(By.NAME, "password").submit()
    wait.until(EC.url_contains("/text-to-speech"))
    time.sleep(2)
    try:
        driver.find_element(By.XPATH, "/html/body/div[6]/div[2]/div[2]/button").click()
    except:
        pass
    time.sleep(2)
    driver.find_element(By.XPATH, "//button[contains(., 'Voice')]").click()
    time.sleep(3)
    driver.find_element(By.XPATH, "//input[@placeholder='Search voice']").send_keys("Brian")
    time.sleep(3)
    driver.find_element(By.XPATH, "//li//p[text()='Brian']").click()
    time.sleep(2)
    driver.find_element(By.XPATH, "//button[contains(., 'Voice Settings')]").click()
    time.sleep(2)
    driver.find_element(By.XPATH, "//button[contains(., 'v2')]").click()

def gerar_e_baixar(driver, texto, index):
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    textarea = driver.find_element(By.XPATH, "//textarea")
    textarea.clear()
    textarea.send_keys(texto)
    time.sleep(5)
    driver.find_element(By.XPATH, "//button[contains(., 'Generate')]").click()
    time.sleep(2)
    download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download')]")))
    before = set(os.listdir(PASTA_AUDIOS))
    download_btn.click()
    for _ in range(30):
        time.sleep(3)
        after = set(os.listdir(PASTA_AUDIOS))
        new_files = after - before
        if new_files:
            break
    if not new_files:
        raise Exception("Download não ocorreu.")
    filename = new_files.pop()
    src = os.path.join(PASTA_AUDIOS, filename)
    ext = os.path.splitext(filename)[1]
    dst = os.path.join(PASTA_AUDIOS, f"narracao{index+1}{ext}")
    os.rename(src, dst)
    return dst

def run_gerar_narracoes(indices):
    with open(ARQUIVO_CENAS, encoding="utf-8") as f:
        cenas = json.load(f)

    logs = []
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
