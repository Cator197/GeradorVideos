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
  const corEstiloVisual = document.getElementById("cor_estilo_visual");
  const corKaraoke = document.getElementById("cor_karaoke");
  const corEstiloVisualContainer = document.getElementById("cor_estilo_visual_container");
  const corKaraokeContainer = document.getElementById("cor_karaoke_container");

  const modo = document.getElementById("modo_legenda");
  const tipoLegenda = document.getElementById("tipo_legenda");
  const qtdePalavras = document.getElementById("qtde_palavras");
  const configASS = document.getElementById("config_ass");
  const configSRT = document.getElementById("config_srt");

  const listaLegenda = document.getElementById("legenda_list");
  const textoBox = document.getElementById("texto_legenda");
  const btnSalvar = document.getElementById("salvar_legenda");
  const editor = document.getElementById("editor_legenda");
  let indiceSelecionado = null;

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

    preview.classList.remove(...estilosClasse, ...animacoesClasse);
    preview.classList.add(estiloSelecionado);
    if (animacaoSelecionada) preview.classList.add(animacaoSelecionada);

    preview.style.fontFamily = fonte.value;
    preview.style.fontSize = `${tamanho.value}px`;
    preview.style.color = cor.value;
  }

  function atualizarCamposExtras() {
    corEstiloVisualContainer.classList.toggle("hidden", estilo.value === "simples");
    corKaraokeContainer.classList.toggle("hidden", animacao.value !== "karaoke");
  }

  [fonte, tamanho, estilo, animacao, cor].forEach(el => {
    el?.addEventListener("change", () => {
      atualizarPreview();
      atualizarCamposExtras();
    });
  });

  atualizarPreview();
  atualizarCamposExtras();

  radios.forEach(radio => {
    radio.addEventListener("change", () => {
      singleInput.disabled = radio.value !== "single";
      fromInput.disabled = radio.value !== "from";
    });
  });

  configASS.classList.add("hidden");
  configSRT.classList.add("hidden");

  tipoLegenda.addEventListener("change", () => {
    const valor = tipoLegenda.value;
    if (valor === "ass") {
      configASS.classList.remove("hidden");
      configSRT.classList.add("hidden");
    } else if (valor === "srt") {
      configASS.classList.add("hidden");
      configSRT.classList.remove("hidden");
    } else {
      configASS.classList.add("hidden");
      configSRT.classList.add("hidden");
    }
  });

  if (btn) {
    btn.addEventListener("click", () => {
      const tipo = tipoLegenda.value;

      if (!tipo) {
        alert("Selecione o tipo de legenda antes de continuar.");
        return;
      }

      const scope = document.querySelector('input[name="scope"]:checked')?.value;

      const payload = {
        scope,
        single_index: parseInt(singleInput.value) || null,
        from_index: parseInt(fromInput.value) || null
      };

      let endpoint = "";

      if (tipo === "ass") {
        endpoint = "/legendas_ass";
        Object.assign(payload, {
          modo: modo.value,
          fonte: fonte.value,
          tamanho: parseInt(tamanho.value),
          estilo: estilo.value,
          animacao: animacao.value,
          cor: cor.value,
          cor_estilo_visual: corEstiloVisual.value,
          cor_karaoke: corKaraoke.value
        });
      } else if (tipo === "srt") {
        endpoint = "/legendas_srt";
        payload.qtde_palavras = parseInt(qtdePalavras.value);
      }

      log.textContent = "📝 Enviando para geração de legendas...\n";
      fill.style.width = "0%";

      fetch(endpoint, {
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
              log.textContent += linha + "\n";
              fill.style.width = Math.min(10 + i * 10, 100) + "%";
            });
            log.textContent += `✅ Legendas ${tipo.toUpperCase()} geradas com sucesso!\n`;
            fill.style.width = "100%";
          }
        })
        .catch(err => {
          log.textContent += `❌ Falha na solicitação: ${err}\n`;
        });
    });
  }

  listaLegenda.addEventListener("change", () => {
    const selected = listaLegenda.options[listaLegenda.selectedIndex];
    indiceSelecionado = parseInt(selected.value);

    fetch(`/get_legenda?index=${indiceSelecionado}`)
      .then(resp => resp.json())
      .then(data => {
        textoBox.value = data.texto || '';
        editor.classList.remove("hidden");
      });
  });

  btnSalvar.addEventListener("click", () => {
    const novoTexto = textoBox.value.trim();

    fetch('/editar_legenda', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        index: indiceSelecionado,
        novo_texto: novoTexto
      })
    })
      .then(resp => resp.json())
      .then(data => {
        if (data.status === 'ok') {
          const msg = document.createElement("div");
          msg.textContent = "✅ Legenda salva!";
          msg.className = "mt-2 text-green-600 font-semibold";
          editor.appendChild(msg);
          setTimeout(() => msg.remove(), 3000);

          listaLegenda.options[indiceSelecionado].textContent =
            `Legenda ${indiceSelecionado + 1} – ${novoTexto.slice(0, 60)}${novoTexto.length > 60 ? '...' : ''}`;
        }
      });
  });
});
