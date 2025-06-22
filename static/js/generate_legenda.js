document.addEventListener("DOMContentLoaded", () => {
  const log = document.getElementById("log");
  const fill = document.getElementById("progress_fill");
  const btn = document.getElementById("generate_legendas");

  const radios = document.querySelectorAll('input[name="scope"]');
  const singleInput = document.getElementById("single_index");
  const fromInput = document.getElementById("from_index");

  const preview = document.getElementById("preview_legenda");
  const fonte = document.getElementById("fonte");
  const tamanho = document.getElementById("tamanho");
  const estilo = document.getElementById("estilo");
  const animacao = document.getElementById("animacao");
  const cor = document.getElementById("cor");
  const modo = document.getElementById("modo_legenda");

  const estilosClasse = [
    "estilo-simples", "estilo-borda", "estilo-sombra", "estilo-glow",
    "estilo-tv", "estilo-retro", "estilo-cartoon", "estilo-inverso", "estilo-fundo"
  ];
  const animacoesClasse = [
    "animacao-fade", "animacao-karaoke", "animacao-zoom", "animacao-deslizar",
    "animacao-piscar", "animacao-pulsar"
  ];

  function atualizarPreview() {
    const estiloSelecionado = `estilo-${estilo.value}`;
    const animacaoSelecionada = animacao.value !== "nenhuma" ? `animacao-${animacao.value}` : "";

    preview.classList.remove(...estilosClasse);
    preview.classList.remove(...animacoesClasse);

    preview.classList.add(estiloSelecionado);
    if (animacaoSelecionada) preview.classList.add(animacaoSelecionada);

    preview.style.fontFamily = fonte.value;
    preview.style.fontSize = `${tamanho.value}px`;
    preview.style.color = cor.value;
  }

  [fonte, tamanho, estilo, animacao, cor].forEach((el) =>
    el.addEventListener("change", atualizarPreview)
  );

  atualizarPreview();

  radios.forEach((radio) => {
    radio.addEventListener("change", () => {
      singleInput.disabled = radio.value !== "single";
      fromInput.disabled = radio.value !== "from";
    });
  });

  if (btn) {
    btn.addEventListener("click", () => {
      const scope = document.querySelector('input[name="scope"]:checked')?.value;
      const payload = {
        scope,
        modo: modo.value,
        fonte: fonte.value,
        tamanho: parseInt(tamanho.value),
        estilo: estilo.value,
        animacao: animacao.value,
        cor: cor.value,
        single_index: parseInt(singleInput.value) || null,
        from_index: parseInt(fromInput.value) || null
      };

      log.textContent = "📝 Enviando para geração de legendas...\n";
      fill.style.width = "0%";

      fetch("/legendas_ass", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          log.textContent += `❌ Erro: ${data.error}\n`;
        } else {
          data.logs.forEach((linha, i) => {
            log.textContent += linha + "\\n";
            fill.style.width = Math.min(10 + i * 10, 100) + "%";
          });
          log.textContent += "✅ Legendas .ASS geradas com sucesso!\n";
          fill.style.width = "100%";
        }
      })
      .catch(err => {
        log.textContent += `❌ Falha na solicitação: ${err}\n`;
      });
    });
  }
});
