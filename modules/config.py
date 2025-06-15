import os
import json
from cryptography.fernet import Fernet

CONFIG_PATH = "configuracoes/config.json"
KEY_PATH = "configuracoes/key.key"

# Cria a pasta se não existir
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

def gerar_chave():
    if not os.path.exists(KEY_PATH):
        with open(KEY_PATH, 'wb') as f:
            f.write(Fernet.generate_key())

def carregar_fernet():
    with open(KEY_PATH, 'rb') as f:
        key = f.read()
    return Fernet(key)

def salvar_config(config_dict):
    gerar_chave()
    fernet = carregar_fernet()
    dados_json = json.dumps(config_dict).encode()
    dados_criptografados = fernet.encrypt(dados_json)

    with open(CONFIG_PATH, 'wb') as f:
        f.write(dados_criptografados)

def carregar_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    fernet = carregar_fernet()
    with open(CONFIG_PATH, 'rb') as f:
        dados_criptografados = f.read()
    dados_json = fernet.decrypt(dados_criptografados).decode()
    return json.loads(dados_json)

def get_config(key: str, default=None):
    config = carregar_config()
    return config.get(key, default)