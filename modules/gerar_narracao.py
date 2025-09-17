"""Geração de narrações utilizando Selenium e ElevenLabs."""
import os
import json
import time
import logging

from webdriver_manager.chrome import ChromeDriverManager

from modules.paths import get_paths
from modules.config import get_config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


path = get_paths()

# Configura logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def iniciar_driver():
    """Inicia o Chrome otimizado e garante a atualização do ChromeDriver.

    Parâmetros:
        Nenhum.

    Retorna:
        selenium.webdriver.Chrome: Instância pronta para uso automatizado.
    """
    logging.info("🔍 Verificando compatibilidade do ChromeDriver com o navegador...")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")  # Desativa extensões
    # chrome_options.add_argument("--disable-gpu")       # (melhor evitar no Windows)
    # chrome_options.add_argument("--no-sandbox")        # (evite em Windows)
    # chrome_options.add_argument("--disable-dev-shm-usage")  # (somente Linux)
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--mute-audio")
    #chrome_options.add_argument("--window-size=1200,800")
    #chrome_options.add_argument("--incognito")
    # chrome_options.add_argument("--user-data-dir=/tmp/selenium_profile")  # (Linux)
    print("Destino do salvamento: ", os.path.abspath(path["audios"]))
    # Desativa carregamento de imagens e fontes
    prefs = {
        "download.default_directory": os.path.abspath(path["audios"]),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.stylesheets": 1,
        "profile.managed_default_content_settings.cookies": 1
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Baixa/usa ChromeDriver compatível com o navegador
    driver_path = ChromeDriverManager().install()
    logging.info(f"✅ ChromeDriver atualizado: {driver_path}")

    # Inicia navegador com o caminho explícito do driver
    logging.info("🚀 Iniciando navegador Chrome com configurações otimizadas")
    return webdriver.Chrome(service=Service(driver_path), options=chrome_options)



def esperar(driver, selector, by=By.XPATH, clickable=False, timeout=20, seerroseguir=True):
    """Aguarda a presença ou clique de um elemento com tratamento opcional de erros.

    Parâmetros:
        driver (selenium.webdriver.Chrome): Navegador utilizado na automação.
        selector (str): Expressão do seletor a ser localizado.
        by (selenium.webdriver.common.by.By): Estratégia de localização.
        clickable (bool): Indica se o elemento deve estar clicável.
        timeout (int): Tempo máximo de espera em segundos.
        seerroseguir (bool): Define se deve retornar ``None`` em caso de erro.

    Retorna:
        selenium.webdriver.remote.webelement.WebElement | None: Elemento encontrado ou ``None``.
    """
    wait = WebDriverWait(driver, timeout)
    cond = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
    try:
        return wait.until(cond((by, selector)))
    except:
        if seerroseguir:
            return None
        else:
            raise


def login(driver, voz="Brian"):
    """Realiza o login e seleciona a voz desejada no site da ElevenLabs.

    Parâmetros:
        driver (selenium.webdriver.Chrome): Navegador autenticado usado no processo.
        voz (str): Nome da voz a ser utilizada na geração.

    Retorna:
        None: As interações são efetuadas diretamente no navegador.
    """

    driver.get("https://elevenlabs.io/app/sign-in")

    wait = WebDriverWait(driver, 20)
    email_input=wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_input.send_keys(get_config("eleven_email"))
    #driver.find_element(By.NAME, "email").send_keys(get_config("eleven_email"))
    #wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(get_config("eleven_email"))
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
    """Gera a narração no site e realiza o download do resultado.

    Parâmetros:
        driver (selenium.webdriver.Chrome): Instância autenticada no serviço.
        texto (str): Texto que será convertido em áudio.
        index (int): Índice da cena utilizada para nomear o arquivo gerado.

    Retorna:
        str: Caminho do arquivo de áudio salvo localmente.
    """

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
        after=set(os.listdir(path["audios"]))
        new_files={f for f in after - before if not f.endswith('.tmp')}
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
    """Processa a geração das narrações selecionadas pelo usuário.

    Parâmetros:
        indices (Iterable[int]): Conjunto de cenas que terão áudio gerado.
        voz (str): Voz escolhida para o serviço de narração.
        fonte (str): Identificador da plataforma utilizada para geração.

    Retorna:
        dict: Estrutura com os logs do processo e cenas atualizadas.
    """

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


    else:
        raise ValueError(f"Fonte de narração '{fonte}' não suportada.")

    with open(path["cenas"], "w", encoding="utf-8") as f:
        json.dump(cenas, f, ensure_ascii=False, indent=2)

    return {"logs": logs, "cenas": cenas}


