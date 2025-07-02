import os
from modules.gerar_ASS import carregar_modelo, gerar_ass_com_whisper, get_paths

# Defina combinações para teste
fontes = ["Arial", "Montserrat"]
tamanhos = [24]
modos = ["linha1", "linha2", "linha3"]
estilos = ["simples", "borda", "sombra"]
animacoes = ["nenhuma", "fade", "zoom", "deslizar", "pulsar", "karaoke", "palavra acumulativa"]

modelo = carregar_modelo()
paths = get_paths()

audio_base = os.path.join(paths["audios"], "exemplo.mp3")
saida_base = paths["legendas"]
os.makedirs(saida_base, exist_ok=True)

count = 0

for fonte in fontes:
    for tamanho in tamanhos:
        for modo in modos:
            for estilo in estilos:
                for animacao in animacoes:
                    nome_saida = f"{fonte}_{tamanho}_{modo}_{estilo}_{animacao}".replace(" ", "_")
                    path_saida = os.path.join(saida_base, f"{nome_saida}.ass")
                    estilo_dict = {
                        "fonte": fonte,
                        "tamanho": tamanho,
                        "cor": "#FFFF00",  # amarelo visível
                        "estilo": estilo,
                        "animacao": animacao
                    }

                    try:
                        gerar_ass_com_whisper(
                            modelo=modelo,
                            path_audio=audio_base,
                            path_saida=path_saida,
                            estilo=estilo_dict,
                            modo=modo
                        )
                        count += 1
                        print(f"✅ Gerado: {nome_saida}.ass")
                    except Exception as e:
                        print(f"❌ Erro em {nome_saida}: {e}")

print(f"\n✅ {count} arquivos de legenda gerados em: {saida_base}")
