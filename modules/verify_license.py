
import json
import base64
import hashlib
import uuid
import subprocess
from datetime import date
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import os
import sys

def resource_path(rel_path: str) -> str:
    """Resolve caminhos relativos mesmo em ambientes empacotados.

    Parâmetros:
        rel_path (str): Caminho relativo ao diretório base do aplicativo.

    Retorna:
        str: Caminho absoluto adequado ao modo de execução atual.
    """
    if getattr(sys, "frozen", False):
        # Executável compilado: usa pasta do executável (não _MEIPASS)
        base = os.path.dirname(sys.executable)
    else:
        # Modo desenvolvimento: usa raiz do projeto
        base = os.path.abspath(".")
    return os.path.join(base, rel_path)

# caminhos empacotados
FERNET_KEY_PATH = resource_path("fernet.key")
PUBLIC_KEY_PATH = resource_path("public_key.pem")

# caminho externo (ao lado do EXE, onde o instalador colocou o cliente.lic)
if getattr(sys, "frozen", False):
    exe_dir       = os.path.dirname(sys.executable)
else:
    exe_dir       = os.path.dirname(os.path.abspath(__file__))
LICENSE_PATH     = os.path.join(exe_dir, "cliente.lic")


def get_disk_serial():
    """Obtém o número de série do disco principal do sistema.

    Parâmetros:
        Nenhum.

    Retorna:
        str: Número de série utilizado para compor o hardware ID.
    """
    output = subprocess.check_output(
        ['wmic', 'diskdrive', 'get', 'SerialNumber'], stderr=subprocess.DEVNULL, text=True
    ).splitlines()
    for line in output:
        line = line.strip()
        if line and line.lower() != 'serialnumber':
            return line
    raise RuntimeError("Não conseguiu ler SerialNumber do disco")

def gerar_hardware_id():
    """Gera o identificador de hardware baseado no MAC e no serial do disco.

    Parâmetros:
        Nenhum.

    Retorna:
        str: Hash SHA-256 representando o dispositivo atual.
    """
    mac = uuid.getnode()
    serial = get_disk_serial()
    return hashlib.sha256(f"{mac}-{serial}".encode()).hexdigest()

def load_fernet():
    """Carrega a chave simétrica utilizada para descriptografar a licença.

    Parâmetros:
        Nenhum.

    Retorna:
        Fernet: Instância configurada com a chave embutida.
    """
    return Fernet(open(FERNET_KEY_PATH, "rb").read())

def load_public_key():
    """Carrega a chave pública empregada na validação da assinatura da licença.

    Parâmetros:
        Nenhum.

    Retorna:
        cryptography.hazmat.primitives.asymmetric.rsa.RSAPublicKey: Chave pronta para verificação.
    """
    data = open(PUBLIC_KEY_PATH, "rb").read()
    return serialization.load_pem_public_key(data)

def verify_license():
    """Valida a licença do cliente verificando assinatura, hardware e expiração.

    Parâmetros:
        Nenhum.

    Retorna:
        None: Encerra o processo com mensagem em caso de falha, imprime sucesso em caso positivo.
    """
    # 1) Leia e decifre o blob
    try:
        blob = open(LICENSE_PATH, "rb").read()
        print(LICENSE_PATH)
    except FileNotFoundError:
        print(LICENSE_PATH)
        sys.exit("❌ Arquivo cliente.lic não encontrado ao lado do exe.")
    f = load_fernet()
    try:
        container_bytes = f.decrypt(blob)
    except Exception as e:
        sys.exit(f"❌ Não foi possível decifrar a licença: {e}")

    # 2) Parse e assinatura
    try:
        container = json.loads(container_bytes)
        lic       = container["license"]
        sig       = base64.b64decode(container["signature"])
    except Exception:
        sys.exit("❌ Formato de licença inválido.")

    pub = load_public_key()
    lic_json = json.dumps(lic, separators=(",",":")).encode()
    try:
        pub.verify(sig, lic_json, padding.PKCS1v15(), hashes.SHA256())
    except Exception:
        sys.exit("❌ Assinatura de licença inválida.")

    # 3) Valida HWID
    if lic["hardware_id"] != gerar_hardware_id():
        sys.exit("❌ Esta licença não é válida para esta máquina.")

    # 4) Valida expiração
    if date.today().isoformat() > lic["expires"]:
        sys.exit(f"❌ Licença expirou em {lic['expires']}.")

    print("✅ Licença OK!")



