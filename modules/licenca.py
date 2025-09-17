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

def carregar_fernet():
    """Carrega a chave Fernet utilizada para criptografar os arquivos de licença.

    Parâmetros:
        Nenhum.

    Retorna:
        Fernet: Instância pronta para cifrar e decifrar conteúdos licenciados.
    """
    return Fernet(open(FERNET_KEY_PATH, "rb").read())

def carregar_licenca():
    """Lê e valida a licença do cliente, verificando assinatura e expiração.

    Parâmetros:
        Nenhum.

    Retorna:
        dict: Dados da licença devidamente verificados.
    """
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

def carregar_config_licenciada():
    """Carrega a configuração licenciada garantindo a integridade e o hardware correto.

    Parâmetros:
        Nenhum.

    Retorna:
        dict: Configuração descriptografada autorizada para a máquina atual.
    """
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


def salvar_config_licenciada(config_dict):
    """Persiste a configuração licenciada de forma criptografada.

    Parâmetros:
        config_dict (dict): Estrutura com créditos, API key e identificadores.

    Retorna:
        None: Os dados são salvos diretamente no arquivo configurado.
    """
    fernet = carregar_fernet()
    dados = json.dumps(config_dict).encode()
    criptografado = fernet.encrypt(dados)
    os.makedirs(os.path.dirname(CONFIG_LICENCIADA_PATH), exist_ok=True)
    with open(CONFIG_LICENCIADA_PATH, "wb") as f:
        f.write(criptografado)

def get_creditos():
    """Obtém a quantidade atual de créditos disponíveis na licença.

    Parâmetros:
        Nenhum.

    Retorna:
        int: Total de créditos restante após a última atualização.
    """
    return carregar_config_licenciada().get("creditos", 0)

def debitar_creditos(qtd):
    """Debita a quantidade informada de créditos da licença ativa.

    Parâmetros:
        qtd (int): Quantidade de créditos a ser subtraída.

    Retorna:
        None: A configuração licenciada é atualizada no disco.
    """
    config = carregar_config_licenciada()
    if config["creditos"] < qtd:
        raise Exception("Créditos insuficientes.")
    config["creditos"] -= qtd
    salvar_config_licenciada(config)

def atualizar_creditos(novo_valor):
    """Define explicitamente o total de créditos disponíveis.

    Parâmetros:
        novo_valor (int): Valor que substituirá o saldo atual de créditos.

    Retorna:
        None: As alterações são salvas imediatamente.
    """
    config = carregar_config_licenciada()
    config["creditos"] = novo_valor
    salvar_config_licenciada(config)

def get_api_key():
    """Recupera a chave de API vinculada à licença instalada.

    Parâmetros:
        Nenhum.

    Retorna:
        str | None: Chave de API registrada, se disponível.
    """
    return carregar_config_licenciada().get("api_key")

def get_hardware_id():
    """Obtém o identificador de hardware calculado para esta máquina.

    Parâmetros:
        Nenhum.

    Retorna:
        str: Hash representando o hardware atual.
    """
    return gerar_hardware_id()
