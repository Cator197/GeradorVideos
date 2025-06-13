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

  // habilitar/desabilitar inputs conforme opção
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
    const response = await fetch("/legendas", {
      method: "POST",
      body: data
    });

    if (!response.ok) {
      log.textContent += "\n❌ Erro ao gerar legendas.";
      return;
    }

    const result = await response.json();
    const linhas = result.logs || [];
    const total = linhas.length;

    linhas.forEach((linha, idx) => {
      const pct = Math.round((idx + 1) / total * 100);
      fill.style.width = pct + "%";
      log.textContent += linha + "\n";
    });
  });
});
