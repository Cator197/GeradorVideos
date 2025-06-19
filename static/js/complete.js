document.addEventListener("DOMContentLoaded", () => {
  const btnGerar = document.getElementById("generate_video");
  const btnPrompt = document.getElementById("processar_prompt");
  const log = document.getElementById("log");
  const fill = document.getElementById("progress_fill");

  // Botão para processar prompt
  btnPrompt.addEventListener("click", async () => {
    const prompt = document.getElementById("initial_prompt").value.trim();
    if (!prompt) {
      log.textContent += "⚠️ Prompt vazio. Preencha antes de processar.\n";
      return;
    }

    try {
      const resp = await fetch("/processar_prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      const data = await resp.json();

      if (data.status === "ok") {
        log.textContent += `✅ ${data.total_cenas} cenas processadas.\n`;
      } else {
        log.textContent += `❌ Erro: ${data.erro}\n`;
      }
    } catch (err) {
      log.textContent += `❌ Erro ao enviar prompt: ${err.message}\n`;
    }
  });

  // Botão para gerar vídeo completo
  btnGerar.addEventListener("click", () => {
    fill.style.width = "0%";
    log.textContent = "🚀 Iniciando geração do vídeo completo...\n";

    const prompt = document.getElementById("initial_prompt").value.trim();
    const nomeVideo = document.getElementById("nome_video").value.trim() || "video_final";

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

    // Monta os parâmetros
    const params = new URLSearchParams({
      nome_video: nomeVideo,
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
        linha.includes("imagem") ||
        linha.includes("salva") ||
        linha.includes("gerada") ||
        linha.includes("Juntando") ||
        linha.includes("Narrando") ||
        linha.includes("Legenda")
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
      log.textContent += "❌ Erro durante o processo.\n";
      source.close();
    };
  });
});
