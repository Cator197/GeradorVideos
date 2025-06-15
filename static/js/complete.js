document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("generate_video");
  const log = document.getElementById("log");
  const fill = document.getElementById("progress_fill");

  btn.addEventListener("click", () => {
    fill.style.width = "0%";
    log.textContent = "🚀 Iniciando geração do vídeo completo...\n";

    // Coleta de opções
    const prompt = document.getElementById("initial_prompt").value.trim();

    const tipoImagem = document.querySelector('input[name="tipo_imagem"]:checked')?.value || "ia";
    const ttsEngine = document.querySelector('input[name="tts_engine"]:checked')?.value || "eleven";
    const vozNarracao = document.getElementById("voz_narracao")?.value || "Brian";

    const usarLegenda = document.getElementById("usar_legenda")?.checked;
    const tipoLegenda = document.querySelector('input[name="tipo_legenda"]:checked')?.value || "hard";
    const corLegenda = document.getElementById("cor_legenda")?.value || "white";
    const tamanhoLegenda = document.getElementById("tamanho_legenda")?.value || 24;
    const posicaoLegenda = document.getElementById("posicao_legenda")?.value || "bottom";

    const unirVideos = document.getElementById("unir_videos")?.checked;
    const exportarCapcut = document.getElementById("criar_capcut")?.checked;
    const usarTrilha = document.getElementById("usar_trilha")?.checked;
    const usarMarca = document.getElementById("usar_marca")?.checked;

    // Monta query string
    const params = new URLSearchParams({
      prompt,
      tipo_imagem: tipoImagem,
      tts_engine: ttsEngine,
      voz: vozNarracao,
      usar_legenda: usarLegenda ? "true" : "false",
      tipo_legenda: tipoLegenda,
      cor_legenda: corLegenda,
      tamanho_legenda: tamanhoLegenda,
      posicao_legenda: posicaoLegenda,
      unir_videos: unirVideos ? "true" : "false",
      exportar_capcut: exportarCapcut ? "true" : "false",
      usar_trilha: usarTrilha ? "true" : "false",
      usar_marca: usarMarca ? "true" : "false"
    });

    const source = new EventSource("/complete_stream?" + params.toString());
    let count = 0;

    source.onmessage = (event) => {
      const linha = event.data;
      log.textContent += linha + "\n";
      log.scrollTop = log.scrollHeight;

      if (
        linha.includes("Prompts processados") ||
        linha.includes("imagem") ||
        linha.includes("salva") ||
        linha.includes("gerada") ||
        linha.includes("Juntando vídeo")
      ) {
        count++;
        const pct = Math.min(5 + count * 7, 100);
        fill.style.width = pct + "%";
      }

      if (linha.includes("Pipeline completa finalizada")) {
        fill.style.width = "100%";
        source.close();
      }
    };

    source.onerror = () => {
      log.textContent += "❌ Erro durante o processo completo.\n";
      source.close();
    };
  });
});
