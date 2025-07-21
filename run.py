import os
import sys, traceback
import socket
import threading
import time, datetime
import webbrowser
from waitress import serve
from app import app, verify_license

# Redirecionar stdout e stderr para clipghost.log
def configurar_logs():
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipghost.log")

    log_path=os.path.join(log_path, "clipghost.log")
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

# Função para registrar mensagens de log persistente
def registrar_log(msg):
    try:
        with open("log_clipghost.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except:
        pass

if __name__ == "__main__":
    print("Iniciando")
    #configurar_logs()
    #verify_license()
    porta_livre = encontrar_porta_livre()
    threading.Thread(target=abrir_navegador, args=(porta_livre,), daemon=True).start()
    #serve(app, host="127.0.0.1", port=porta_livre)
    app.run(debug=True, port=porta_livre)

    # try:
    #
    #
    #     porta_livre=encontrar_porta_livre()
    #     registrar_log(f"✔️ Porta livre encontrada: {porta_livre}")
    #
    #     threading.Thread(target=abrir_navegador, args=(porta_livre,), daemon=True).start()
    #
    #     # Inicie seu app normalmente
    #     app.run(debug=True, port=porta_livre)
    #
    # except Exception as e:
    #     registrar_log("❌ Erro ao iniciar aplicação:")
    #     registrar_log(traceback.format_exc())
    #     raise  # para também exibir erro no terminal, se visível