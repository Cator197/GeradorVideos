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
CONFIG_LICENCIADA_PATH = resource_path("config_licenciado.json")
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
    print("📥 Tentando carregar config_licenciado.json")

    if not os.path.exists(CONFIG_LICENCIADA_PATH):
        print(f"❌ Arquivo não encontrado: {CONFIG_LICENCIADA_PATH}")
        raise Exception("Arquivo de configuração licenciada não encontrado.")

    try:
        fernet = carregar_fernet()
        with open(CONFIG_LICENCIADA_PATH, "rb") as f:
            dados = f.read()
        print("🔐 Lendo e tentando descriptografar o conteúdo...")
        dados_json = fernet.decrypt(dados).decode()
        config = json.loads(dados_json)
    except Exception as e:
        print("❌ Erro ao descriptografar:", e)
        raise Exception("Erro ao ler a configuração licenciada.")

    hw_local = gerar_hardware_id()
    print("🔍 Verificando hardware_id...")
    if config.get("hardware_id") != hw_local:
        print(f"❌ HWID incorreto. Esperado: {hw_local}, Recebido: {config.get('hardware_id')}")
        raise Exception("Configuração não autorizada para este dispositivo.")

    print("✅ Configuração licenciada carregada com sucesso.")
    return config


# Salvar config licenciada
def salvar_config_licenciada(config_dict):
    fernet = carregar_fernet()
    dados = json.dumps(config_dict).encode()
    criptografado = fernet.encrypt(dados)
    os.makedirs(os.path.dirname(CONFIG_LICENCIADA_PATH), exist_ok=True)
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
