import os
import json
from google.cloud import texttospeech
from modules.config import get_config
from modules.gerar_narracao import get_paths

# Caminho absoluto para o arquivo de chave JSON (adicione aqui o caminho correto)
#os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:\Users\caiod\Desktop\Nova pasta\gerador/sua-chave.json"

def gerar_google_audio(texto: str, voz: str, index: int) -> str:
    """Gera narração via API Google Cloud TTS e salva como MP3."""
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=texto)

    # Define o idioma com base no nome da voz (ex: pt-br-Hélio → pt-BR)
    partes = voz.split("-")
    language_code = f"{partes[0]}-{partes[1]}"

    voice_params = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voz
    )

    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = client.synthesize_speech(
        input=input_text,
        voice=voice_params,
        audio_config=audio_config
    )

    paths = get_paths()
    out_path = os.path.join(paths["audios"], f"narracao{index + 1}.mp3")
    with open(out_path, "wb") as out:
        out.write(response.audio_content)

    return out_path


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from modules.gerar_narracao import get_paths

def gerar_com_gemini_selenium(driver, texto, index):
    """Gera narração no site TTS do Google Cloud (ou Gemini Studio) e baixa o áudio."""
    paths = get_paths()
    wait = WebDriverWait(driver, 20)

    driver.get("https://cloud.google.com/text-to-speech")

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
