document.addEventListener("DOMContentLoaded", () => {
  const log = document.getElementById("log");
  const barra = document.getElementById("barra_indeterminada");
  const btn = document.getElementById("generate_legendas");

  const radios = document.querySelectorAll('input[name="scope"]');
  const singleInput = document.getElementById("single_index");
  const fromInput = document.getElementById("from_index");

  const preview = document.getElementById("preview_legenda");
  const fonte = document.getElementById("fonte");
  const tamanho = document.getElementById("tamanho");
  const estilo = document.getElementById("estilo");
  const animacao = document.getElementById("animacao");

  const corPrimaria = document.getElementById("cor");
  const corOutline = document.getElementById("cor_outline");
  const corBack = document.getElementById("cor_back");
  const corSecundaria = document.getElementById("cor_secundaria");

  const corOutlineContainer = document.getElementById("cor_outline_container");
  const corBackContainer = document.getElementById("cor_back_container");
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
    "estilo-simples", "estilo-borda", "estilo-sombra", "estilo-glow", "estilo-tv"
  ];
  const animacoesClasse = [
    "animacao-fade", "animacao-karaoke", "animacao-zoom", "animacao-deslizar"
  ];

  function iniciarProgresso() {
    barra.classList.remove("hidden");
  }

  function pararProgresso() {
    barra.classList.add("hidden");
  }

  function atualizarPreview() {
    const estiloSelecionado = `estilo-${estilo.value}`;
    const animacaoSelecionada = animacao.value !== "nenhuma" ? `animacao-${animacao.value}` : "";

    preview.classList.remove(...estilosClasse, ...animacoesClasse);
    preview.classList.add(estiloSelecionado);
    if (animacaoSelecionada) preview.classList.add(animacaoSelecionada);

    preview.style.fontFamily = fonte.value;
    preview.style.fontSize = `${tamanho.value}px`;
    preview.style.color = corPrimaria.value;
  }

  function atualizarCamposExtras() {
    const val = estilo.value;
    corOutlineContainer.classList.toggle("hidden", !["borda", "glow", "tv"].includes(val));
    corBackContainer.classList.toggle("hidden", val !== "sombra");
    corKaraokeContainer.classList.toggle("hidden", animacao.value !== "karaoke");
  }

  [fonte, tamanho, estilo, animacao, corPrimaria].forEach(el => {
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
    configASS.classList.toggle("hidden", valor !== "ass");
    configSRT.classList.toggle("hidden", valor !== "srt");
  });

  if (btn) {
    btn.addEventListener("click", () => {
      const tipo = tipoLegenda.value;
      if (!tipo) return alert("Selecione o tipo de legenda antes de continuar.");

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
          cor_primaria: corPrimaria.value,
          cor_outline: corOutline.value,
          cor_back: "#000000",
          cor_secundaria: corSecundaria.value
        });
      } else if (tipo === "srt") {
        endpoint = "/legendas_srt";
        payload.qtde_palavras = parseInt(qtdePalavras.value);
      }

      iniciarProgresso();
      log.textContent = "📝 Enviando para geração de legendas...\n";

      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        pararProgresso();
        if (data.error) {
          log.textContent += `❌ Erro: ${data.error}\n`;
        } else {
          data.logs.forEach(linha => log.textContent += linha + "\n");
          log.textContent += `✅ Legendas ${tipo.toUpperCase()} geradas com sucesso!\n`;
        }
      })
      .catch(err => {
        pararProgresso();
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
      body: JSON.stringify({ index: indiceSelecionado, novo_texto: novoTexto })
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
