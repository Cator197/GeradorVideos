import os
import sys
import socket
import threading
import time
import webbrowser
from waitress import serve
from app import app, verify_license

# Redirecionar stdout e stderr para clipghost.log
def configurar_logs():
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipghost.log")
    print("LOG SENDO GRAVADO EM: ",log_path)
    log_file = open(log_path, "a", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file

# Função para encontrar uma porta livre
def encontrar_porta_livre(inicial=5000, final=5100):
    for porta in range(inicial, final):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', porta))
                return porta
            except OSError:
                continue
    raise RuntimeError("Nenhuma porta disponível entre 5000 e 5100.")

# Função para abrir o navegador após iniciar o servidor
def abrir_navegador(porta):
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{porta}")

if __name__ == "__main__":
    configurar_logs()
    #verify_license()
    porta_livre = encontrar_porta_livre()
    threading.Thread(target=abrir_navegador, args=(porta_livre,), daemon=True).start()
    serve(app, host="127.0.0.1", port=porta_livre)
