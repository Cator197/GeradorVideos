document.addEventListener("DOMContentLoaded", () => {
  const lista = document.getElementById("narracao_list");
  const audio = document.getElementById("preview_audio");
  const source = document.getElementById("audio_source");
  const logArea = document.getElementById("log");
  const fill = document.getElementById("progress_fill");

  const btnGerar = document.getElementById("generate_narracoes");
  const btnRemover = document.getElementById("remover_silencio");
  const silencioMin = document.getElementById("silencio_min");

  // Duplo clique para tocar narração
  if (lista && audio && source) {
    lista.addEventListener("dblclick", () => {
      const selected = lista.options[lista.selectedIndex];
      const url = selected?.dataset?.url;

      if (url) {
        source.src = url;
        audio.load();

        // Timeout pequeno para evitar AbortError
        setTimeout(() => {
          audio.play().catch((err) =>
            console.warn("Falha ao reproduzir:", err.message)
          );
        }, 100);
      }
    });
  }

  // Habilita e desabilita campos de índice
  const radios = document.querySelectorAll('input[name="scope"]');
  const singleInput = document.getElementById("single_index");
  const fromInput = document.getElementById("from_index");

  radios.forEach((radio) => {
    radio.addEventListener("change", () => {
      singleInput.disabled = radio.value !== "single";
      fromInput.disabled = radio.value !== "from";
    });
  });

  // Geração de narrações
  if (btnGerar) {
    btnGerar.addEventListener("click", () => {
      const scope = document.querySelector('input[name="scope"]:checked')?.value;
      const index = singleInput.value;
      const fromIndex = fromInput.value;

      let query = `scope=${scope}`;
      if (scope === "single" && index) query += `&index=${index}`;
      if (scope === "from" && fromIndex) query += `&from_index=${fromIndex}`;

      fill.style.width = "0%";
      logArea.textContent = "🎤 Iniciando geração de narrações...\n";

      const source = new EventSource("/narracao_stream?" + query);
      let count = 0;

      source.onmessage = (event) => {
        const linha = event.data;
        logArea.textContent += linha + "\n";
        logArea.scrollTop = logArea.scrollHeight;

        if (linha.includes("Narração") || linha.includes("salva") || linha.includes("gerada")) {
          count++;
          fill.style.width = Math.min(5 + count * 10, 100) + "%";
        }

        if (linha.includes("✅ Geração de narrações finalizada")) {
          fill.style.width = "100%";
          source.close();
        }
      };

      source.onerror = () => {
        logArea.textContent += "❌ Erro no servidor ou conexão encerrada.\n";
        source.close();
      };
    });
  }

  // Remover silêncio dos áudios
  if (btnRemover && silencioMin) {
    btnRemover.addEventListener("click", () => {
      const valor = silencioMin.value || "0.3";
      logArea.textContent += `🧹 Removendo silêncio com mínimo de ${valor}s...\n`;

      fetch(`/remover_silencio?min_silence=${valor}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.status === "ok") {
            logArea.textContent += `✅ Silêncios removidos de ${data.arquivos} arquivos.\n`;
          } else {
            logArea.textContent += `❌ Erro: ${data.error}\n`;
          }
        })
        .catch((err) => {
          logArea.textContent += `❌ Erro na requisição: ${err}\n`;
        });
    });
  }
});
