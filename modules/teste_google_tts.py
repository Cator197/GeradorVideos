import os
from google.cloud import texttospeech

# 🔧 Substitua com o caminho para sua chave
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/CAMINHO/PARA/SUA_CHAVE.json"

# Texto de exemplo
texto = "Olá! Este é um teste da voz Hélio usando a API do Google Text-to-Speech."

# Cria cliente
client = texttospeech.TextToSpeechClient()

# Define entrada de texto
input_text = texttospeech.SynthesisInput(text=texto)

# Define a voz (português brasileiro)
voz = texttospeech.VoiceSelectionParams(
    language_code="pt-BR",
    name="pt-br-Standard-A"
    # Exemplo de outras vozes: pt-br-Wavenet-A, en-US-Wavenet-D
)

# Configura saída
config_audio = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

# Requisição de síntese
response = client.synthesize_speech(
    input=input_text,
    voice=voz,
    audio_config=config_audio
)

# Salva arquivo
with open("teste_google_narracao.mp3", "wb") as out:
    out.write(response.audio_content)

print("✅ Narração gerada: teste_google_narracao.mp3")
