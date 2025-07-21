# modules/licenca.py

import os
import json
from cryptography.fernet import Fernet
from datetime import date
from modules.verify_license import resource_path, gerar_hardware_id, load_public_key
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


# Caminhos dos arquivos
CONFIG_LICENCIADA_PATH = "configuracoes/config_licenciado.json"
FERNET_KEY_PATH = resource_path("fernet.key")
LICENSE_PATH = resource_path("cliente.lic")

# Carregar chave fernet
def carregar_fernet():
    return Fernet(open(FERNET_KEY_PATH, "rb").read())

# Validar assinatura da licença
def carregar_licenca():
    fernet = carregar_fernet()
    blob = open(LICENSE_PATH, "rb").read()
    container_bytes = fernet.decrypt(blob)

    container = json.loads(container_bytes)
    lic = container["license"]
    sig = base64.b64decode(container["signature"])

    pub = load_public_key()
    lic_json = json.dumps(lic, separators=(",", ":")).encode()
    pub.verify(sig, lic_json, padding.PKCS1v15(), hashes.SHA256())

    # Validação de expiração
    if date.today().isoformat() > lic["expires"]:
        raise Exception(f"Licença expirada em {lic['expires']}")

    return lic

# Carregar configuração licenciada (criptografada e validada)
def carregar_config_licenciada():
    if not os.path.exists(CONFIG_LICENCIADA_PATH):
        raise Exception("Arquivo de configuração licenciada não encontrado.")

    fernet = carregar_fernet()
    dados = fernet.decrypt(open(CONFIG_LICENCIADA_PATH, "rb").read()).decode()
    config = json.loads(dados)

    # Valida hardware_id
    hw_local = gerar_hardware_id()
    if config.get("hardware_id") != hw_local:
        raise Exception("Configuração não autorizada para este dispositivo.")

    return config

# Salvar config licenciada
def salvar_config_licenciada(config_dict):
    fernet = carregar_fernet()
    dados = json.dumps(config_dict).encode()
    criptografado = fernet.encrypt(dados)
    with open(CONFIG_LICENCIADA_PATH, "wb") as f:
        f.write(criptografado)

# Expor funções úteis
def get_creditos():
    return carregar_config_licenciada().get("creditos", 0)

def debitar_creditos(qtd):
    config = carregar_config_licenciada()
    if config["creditos"] < qtd:
        raise Exception("Créditos insuficientes.")
    config["creditos"] -= qtd
    salvar_config_licenciada(config)

def atualizar_creditos(novo_valor):
    config = carregar_config_licenciada()
    config["creditos"] = novo_valor
    salvar_config_licenciada(config)

def get_api_key():
    return carregar_config_licenciada().get("api_key")

def get_hardware_id():
    return gerar_hardware_id()
