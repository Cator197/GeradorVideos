"""Gerenciamento de configuração criptografada do aplicativo."""

import os
import json
from cryptography.fernet import Fernet

CONFIG_PATH = "configuracoes/config.json"
KEY_PATH = "configuracoes/key.key"

# Cria a pasta se não existir
os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

def gerar_chave():
    """Gera e salva uma chave criptográfica se ainda não existir.

    Parâmetros:
        Nenhum.

    Retorna:
        None: A chave é gravada no caminho configurado.
    """
    if not os.path.exists(KEY_PATH):
        with open(KEY_PATH, "wb") as f:
            f.write(Fernet.generate_key())

def carregar_fernet():
    """Carrega um objeto Fernet para criptografia e descriptografia de dados.

    Parâmetros:
        Nenhum.

    Retorna:
        Fernet: Instância inicializada com a chave salva.
    """
    with open(KEY_PATH, "rb") as f:
        key = f.read()
    return Fernet(key)

def salvar_config(config_dict):
    """Salva o dicionário de configuração de forma criptografada.

    Parâmetros:
        config_dict (dict): Configurações fornecidas pelo usuário.

    Retorna:
        None: Os dados são armazenados no arquivo protegido.
    """
    gerar_chave()
    fernet = carregar_fernet()
    dados_json = json.dumps(config_dict).encode()
    dados_criptografados = fernet.encrypt(dados_json)

    with open(CONFIG_PATH, 'wb') as f:
        f.write(dados_criptografados)

def carregar_config():
    """Carrega e descriptografa o arquivo de configuração.

    Parâmetros:
        Nenhum.

    Retorna:
        dict: Configurações armazenadas ou dicionário vazio.
    """
    if not os.path.exists(CONFIG_PATH):
        return {}
    fernet = carregar_fernet()
    with open(CONFIG_PATH, "rb") as f:
        dados_criptografados = f.read()
    dados_json = fernet.decrypt(dados_criptografados).decode()
    return json.loads(dados_json)

def get_config(key: str, default=None):
    """Recupera um valor de configuração ou retorna o padrão informado.

    Parâmetros:
        key (str): Nome da chave desejada.
        default (Any): Valor retornado quando a chave não existe.

    Retorna:
        Any: Valor armazenado na configuração ou o padrão fornecido.
    """
    config = carregar_config()
    return config.get(key, default)
