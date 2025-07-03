import sys
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
    """
    Retorna o caminho absoluto de um arquivo empacotado (fernet.key, public_key.pem)
    ou, em dev, relativo ao script.
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
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
    output = subprocess.check_output(
        ['wmic', 'diskdrive', 'get', 'SerialNumber'], stderr=subprocess.DEVNULL, text=True
    ).splitlines()
    for line in output:
        line = line.strip()
        if line and line.lower() != 'serialnumber':
            return line
    raise RuntimeError("Não conseguiu ler SerialNumber do disco")

def gerar_hardware_id():
    mac = uuid.getnode()
    serial = get_disk_serial()
    return hashlib.sha256(f"{mac}-{serial}".encode()).hexdigest()

def load_fernet():
    return Fernet(open(FERNET_KEY_PATH, "rb").read())

def load_public_key():
    data = open(PUBLIC_KEY_PATH, "rb").read()
    return serialization.load_pem_public_key(data)

def verify_license():
    # 1) Leia e decifre o blob
    try:
        blob = open(LICENSE_PATH, "rb").read()
    except FileNotFoundError:
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



