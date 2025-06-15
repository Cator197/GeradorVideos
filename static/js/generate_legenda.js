document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("form_generate_legendas");
  const btn = document.getElementById("generate_legendas");
  const fill = document.getElementById("progress_fill");
  const log  = document.getElementById("log");

  const scope_all    = document.querySelector('input[value="all"]');
  const scope_single = document.querySelector('input[value="single"]');
  const scope_from   = document.querySelector('input[value="from"]');
  const input_single = document.getElementById("single_index");
  const input_from   = document.getElementById("from_index");

  // Habilita ou desabilita inputs conforme a opção selecionada
  document.querySelectorAll('input[name="scope"]').forEach(el => {
    el.addEventListener("change", () => {
      input_single.disabled = !scope_single.checked;
      input_from.disabled   = !scope_from.checked;
    });
  });

  btn.addEventListener("click", async () => {
    fill.style.width = "0%";
    log.textContent = "⏳ Iniciando geração de legendas...\n";

    const data = new FormData(form);
    const params = new URLSearchParams(data).toString();

    const source = new EventSource("/legendas_stream?" + params);
    let count = 0;

    source.onmessage = (event) => {
      const linha = event.data;

      // Atualiza log
      log.textContent += linha + "\n";
      log.scrollTop = log.scrollHeight;

      // Atualiza barra se for linha relevante
      if (linha.includes("Gerando legenda") || linha.includes("Legenda") || linha.includes("salva")) {
        count++;
        const total = document.getElementById("legenda_list").length || 1;
        const pct = Math.round((count / total) * 100);
        fill.style.width = pct + "%";
      }

      // Finaliza SSE automaticamente
      if (linha.includes("Fim do processo")) {
        source.close();
      }
    };

    source.onerror = () => {
      log.textContent += "❌ Erro no servidor ou conexão encerrada.\n";
      source.close();
    };
  });
});
