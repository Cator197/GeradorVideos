import os
import time
import json
import getpass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Módulo 3: gerar_narracoes.py
# Automatiza o ElevenLabs TTS via interface web (Selenium)
# Pré-requisitos:
#  - pip install selenium
#  - ChromeDriver no PATH (mesma versão do Chrome)

# Configurações de caminhos
ARQUIVO_CENAS = "cenas_com_imagens.json"
PASTA_AUDIOS = "audios_narracoes"
os.makedirs(PASTA_AUDIOS, exist_ok=True)
# Credenciais do ElevenLabs
EMAIL = "cdgproducoes2@gmail.com" #os.getenv("ELEVEN_EMAIL") or input("Email ElevenLabs: ")
PASSWORD = "@Producoes147856#2"#os.getenv("ELEVEN_PASSWORD") or getpass.getpass("Senha ElevenLabs: ")

# Configura Selenium para download automático
download_dir = os.path.abspath(PASTA_AUDIOS)
chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})
# chrome_options.add_argument("--headless")  # descomente para rodar sem UI

driver = webdriver.Chrome(options=chrome_options)

def login():
    driver.get("https://elevenlabs.io/app/speech-synthesis/text-to-speech")
    wait = WebDriverWait(driver, 10)
    # Ajuste os seletores conforme a página real
    email_input = wait.until(EC.visibility_of_element_located((By.NAME, "email")))
    pass_input  = driver.find_element(By.NAME, "password")
    email_input.send_keys(EMAIL)
    pass_input.send_keys(PASSWORD)
    pass_input.submit()
    wait.until(EC.url_contains("/text-to-speech"))
    textarea = wait.until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/div/div[1]/div/div[1]/div/div/div/div[1]/div[2]/div[2]/div")))
    #textarea.clear()

    #fecha uma tela tipo popup
    time.sleep(2)
    driver.find_element(By.XPATH,
                        "/html/body/div[6]/div[2]/div[2]/button").click()

    #clica no seletor de voz
    time.sleep(2)
    driver.find_element(By.XPATH,
                            "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div/div[2]/div[1]/div/button").click()
    #digita a voz
    time.sleep(3)
    driver.find_element(By.XPATH,
                        "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div/div/div[1]/input").send_keys("Brian")

    #clica no primeiro
    time.sleep(5)
    driver.find_element(By.XPATH,
                        "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div/div[2]/div/div/div[2]/div/div[1]/ul/li/div[2]/div[2]/div/div[1]/div[1]/p").click()

    #clica nno seletor de modelo
    time.sleep(2)
    driver.find_element(By.XPATH,
                        "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div[1]/div[2]/div/div[2]/div[2]/div/div[1]/div/button").click()

    #escolhe o v2
    time.sleep(2)
    driver.find_element(By.XPATH,
                        "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/section/div/div/div[2]/div[2]/div[2]/div[1]/button[2]").click()


def gerar_e_baixar(texto, index):
    # Navega para TTS
    #driver.get("https://elevenlabs.io/tts")
    wait = WebDriverWait(driver, 20)
    # Campo de texto


    time.sleep(3)
    driver.find_element(By.XPATH,
                        "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/div/div[1]/textarea").clear()
    driver.find_element(By.XPATH,
                        "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/div/div[1]/textarea").send_keys(texto)

    time.sleep(5)
    # Botão gerar (ajuste o seletor)
    generate_btn = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[4]/div[3]/div/main/div/div/div/div[2]/div[2]/div/div[2]/div/button[2]")
    generate_btn.click()
    # Aguarda botão de download
    time.sleep(2)
    download_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div[4]/div[2]/div/div/div/div[3]/button")))
    before = set(os.listdir(download_dir))
    download_btn.click()
    # Espera arquivo novo
    for _ in range(30):
        time.sleep(1)
        after = set(os.listdir(download_dir))
        new_files = after - before
        if new_files:
            break
    if not new_files:
        raise Exception("Download não ocorreu.")
    filename = new_files.pop()
    src = os.path.join(download_dir, filename)
    ext = os.path.splitext(filename)[1]
    dst = os.path.join(download_dir, f"narracao{index+1}{ext}")
    os.rename(src, dst)
    print(f"✅ Áudio narracao{index+1}{ext} salvo.")
    return dst


def main():
    login()
    with open(ARQUIVO_CENAS, encoding="utf-8") as f:
        cenas = json.load(f)
    for i, cena in enumerate(cenas):
        texto = cena.get("narracao")
        if not texto:
            continue
        print(f"Gerando narração {i+1}: {texto[:30]}...")
        gerar_e_baixar(texto, i)
    driver.quit()

if __name__ == "__main__":
    main()
