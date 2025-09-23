# modules/licenca.py  (substituir/mesclar com o existente)

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
SHADOW_SERIAL_PATH = resource_path("configuracoes/serial.shadow")  # local 'difícil de apagar'

def carregar_fernet():
    return Fernet(open(FERNET_KEY_PATH, "rb").read())

# --- Funções já existentes (carregar_licenca, carregar_config_licenciada, salvar_config_licenciada) ---
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
    if date.today().isoformat() > lic["expires"]:
        raise Exception(f"Licença expirada em {lic['expires']}")
    return lic

def carregar_config_licenciada():
    if not os.path.exists(CONFIG_LICENCIADA_PATH):
        raise Exception("Arquivo de configuração licenciada não encontrado.")
    try:
        fernet = carregar_fernet()
        with open(CONFIG_LICENCIADA_PATH, "rb") as f:
            dados = f.read()
        dados_json = fernet.decrypt(dados).decode()
        config = json.loads(dados_json)
    except Exception as e:
        raise Exception("Erro ao ler a configuração licenciada.") from e
    hw_local = gerar_hardware_id()
    if config.get("hardware_id") != hw_local:
        raise Exception("Configuração não autorizada para este dispositivo.")
    return config

def salvar_config_licenciada(config_dict):
    fernet = carregar_fernet()
    dados = json.dumps(config_dict).encode()
    criptografado = fernet.encrypt(dados)
    os.makedirs(os.path.dirname(CONFIG_LICENCIADA_PATH), exist_ok=True)
    with open(CONFIG_LICENCIADA_PATH, "wb") as f:
        f.write(criptografado)

# --- Novos helpers de estado e shadow ------------------------------------
def ler_estado_creditos():
    """
    Retorna um dict com keys:
    { hardware_id, creditos, api_key, redeemed_ids (list), last_serial (int) }
    """
    try:
        cfg = carregar_config_licenciada()
    except Exception:
        # inicializar estado padrão se não existir
        cfg = {
            "hardware_id": gerar_hardware_id(),
            "creditos": 0,
            "api_key": "",
            "redeemed_ids": [],
            "last_serial": 0
        }

    # garantir campos
    cfg.setdefault("redeemed_ids", [])
    cfg.setdefault("last_serial", 0)
    return cfg

def salvar_estado_creditos(estado: dict):
    # garante chaves mínimas
    estado.setdefault("hardware_id", gerar_hardware_id())
    estado.setdefault("creditos", 0)
    estado.setdefault("redeemed_ids", [])
    estado.setdefault("last_serial", 0)
    salvar_config_licenciada(estado)
    # atualiza shadow serial
    gravar_shadow_serial(int(estado["last_serial"]))

def ler_shadow_serial() -> int:
    """Lê o serial no arquivo sombra; retorna 0 se inexistente / inválido."""
    try:
        if os.path.exists(SHADOW_SERIAL_PATH):
            with open(SHADOW_SERIAL_PATH, "r", encoding="utf-8") as f:
                txt = f.read().strip()
            return int(txt) if txt.isdigit() else 0
    except Exception:
        pass
    return 0

def gravar_shadow_serial(serial: int):
    try:
        os.makedirs(os.path.dirname(SHADOW_SERIAL_PATH), exist_ok=True)
        with open(SHADOW_SERIAL_PATH, "w", encoding="utf-8") as f:
            f.write(str(int(serial)))
    except Exception:
        pass

# --- Funções de consumo já existentes reimplementadas em cima do estado ----
def get_creditos():
    return ler_estado_creditos().get("creditos", 0)

def debitar_creditos(qtd):
    estado = ler_estado_creditos()
    if estado.get("creditos", 0) < qtd:
        raise Exception("Créditos insuficientes.")
    estado["creditos"] -= qtd
    salvar_estado_creditos(estado)

def atualizar_creditos(novo_valor):
    estado = ler_estado_creditos()
    estado["creditos"] = int(novo_valor)
    salvar_estado_creditos(estado)

def get_api_key():
    return ler_estado_creditos().get("api_key")
def get_hardware_id():
    return gerar_hardware_id()
