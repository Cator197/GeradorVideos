import os
import sys, traceback
import socket
import threading
import time
from datetime import datetime
import webbrowser
from waitress import serve
from app import app, verify_license
from modules.verify_license import resource_path

def configurar_logs():
    # Caminho da pasta de configuração (ao lado do script ou exe)
    config_dir = resource_path("configuracoes")
    os.makedirs(config_dir, exist_ok=True)

    # Caminho do arquivo de log
    log_path = os.path.join(config_dir, "clipghost.log")
    print("Local onde está gravando o log: ", log_path)
    # Abre o log em modo append
    log_file = open(log_path, "a", encoding="utf-8")

    # Marca a nova execução com data/hora
    log_file.write("\n--- Nova execução ---\n")
    log_file.write(f"🕓 {datetime.now().isoformat()}\n\n")
    log_file.flush()

    # Redireciona stdout e stderr para o log
    #sys.stdout = log_file
    sys.stderr = log_file

    print(f"📄 LOG SENDO GRAVADO EM: {log_path}")

    # Captura exceções não tratadas
    def excecao_nao_tratada(exc_type, exc_value, exc_traceback):
        print("❌ Exceção não tratada:")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    sys.excepthook = excecao_nao_tratada

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
    print("Iniciando")
    configurar_logs()
    verify_license()
    porta_livre = encontrar_porta_livre()
    threading.Thread(target=abrir_navegador, args=(porta_livre,), daemon=True).start()
    serve(app, host="127.0.0.1", port=porta_livre)
    #app.run(debug=True, port=porta_livre)

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