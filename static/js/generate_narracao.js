document.addEventListener("DOMContentLoaded", () => {
  const lista     = document.getElementById("narracao_list");
  const audio     = document.getElementById("preview_audio");
  const source    = document.getElementById("audio_source");
  const logArea   = document.getElementById("log");
  const fill      = document.getElementById("progress_fill");

  const btnGerar  = document.getElementById("generate_narracoes");
  const btnRemover = document.getElementById("remover_silencio");
  const silencioMin = document.getElementById("silencio_min");

  const editor      = document.getElementById("editor_narracao");
  const textoBox    = document.getElementById("texto_narracao");
  const btnSalvar   = document.getElementById("salvar_narracao");

  const singleInput = document.getElementById("single_index");
  const fromInput   = document.getElementById("from_index");
  const customInput = document.getElementById("custom_indices_narracao");

  const fonteSelect = document.getElementById("fonte");
  const vozSelect   = document.getElementById("voz");
  const btnPreviewVoz = document.getElementById("preview_voz");

  let indiceSelecionado = null;

  const vozesPorFonte = {
    elevenlabs: [
      { value: "Brian", label: "Brian (inglês)" },
      { value: "Matilda", label: "Matilda (inglês)" },
      { value: "Bella", label: "Bella (inglês)" },
      { value: "Antoni", label: "Antoni (espanhol)" },
      { value: "Elli", label: "Elli (alemão)" },
      { value: "Helena", label: "Helena (português)" }
    ],
    gemini: [
      { value: "pt-br-Hélio", label: "Hélio (português Brasil)" },
      { value: "en-us-Max", label: "Max (inglês EUA)" },
      { value: "es-mx-Luisa", label: "Luisa (espanhol México)" }
    ]
  };

  function atualizarVozes(fonte) {
    const vozes = vozesPorFonte[fonte] || [];
    vozSelect.innerHTML = "";
    vozes.forEach(v => {
      const opt = document.createElement("option");
      opt.value = v.value;
      opt.textContent = v.label;
      vozSelect.appendChild(opt);
    });
  }

  fonteSelect.addEventListener("change", () => {
    atualizarVozes(fonteSelect.value);
  });

  // Inicializar com a fonte atual
  atualizarVozes(fonteSelect.value);

  // Preview da voz selecionada
  btnPreviewVoz.addEventListener("click", () => {
    const fonte = fonteSelect.value;
    const voz = vozSelect.value;
    const path = `/static/vozes/${fonte}/${voz}.mp3`;

    const audioPreview = new Audio(path);
    audioPreview.play().catch(() => {
      alert("❌ Amostra de voz não encontrada.");
    });
  });

  // Duplo clique para tocar narração
  if (lista && audio && source) {
    lista.addEventListener("dblclick", () => {
      const selected = lista.options[lista.selectedIndex];
      const url = selected?.dataset?.url;

      if (url) {
        source.src = url;
        audio.load();
        setTimeout(() => {
          audio.play().catch((err) =>
            console.warn("Falha ao reproduzir:", err.message)
          );
        }, 100);
      }
    });
  }

  // Clique simples: buscar texto diretamente do JSON
  lista.addEventListener("change", () => {
    const selected = lista.options[lista.selectedIndex];
    const url = selected?.dataset?.url;
    indiceSelecionado = parseInt(selected.value);

    if (url) {
      source.src = url;
      audio.load();
    }

    fetch(`/get_narracao?index=${indiceSelecionado}`)
      .then(resp => resp.json())
      .then(data => {
        textoBox.value = data.texto || '';
        editor.classList.remove("hidden");
      })
      .catch(() => {
        textoBox.value = '';
        editor.classList.remove("hidden");
      });
  });

  // Salvar texto no JSON (sem gerar áudio)
  btnSalvar.addEventListener("click", () => {
    const novoTexto = textoBox.value.trim();

    fetch('/editar_narracao', {
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
          msg.textContent = "✅ Texto salvo com sucesso!";
          msg.className = "mt-2 text-green-600 font-semibold";
          editor.appendChild(msg);
          setTimeout(() => msg.remove(), 3000);

          lista.options[indiceSelecionado].textContent =
            `Narração ${indiceSelecionado + 1} – ${novoTexto.slice(0, 60)}${novoTexto.length > 60 ? '...' : ''}`;
        } else {
          alert("❌ Erro ao salvar.");
        }
      })
      .catch(() => alert("❌ Erro na comunicação com o servidor."));
  });

  // Habilita e desabilita campos de índice
  const radios = document.querySelectorAll('input[name="scope"]');

  radios.forEach((radio) => {
    radio.addEventListener("change", () => {
      singleInput.disabled = radio.value !== "single";
      fromInput.disabled = radio.value !== "from";
      customInput.disabled = radio.value !== "custom";
    });
  });

  // Geração de narrações
  if (btnGerar) {
    btnGerar.addEventListener("click", () => {
      const scope = document.querySelector('input[name="scope"]:checked')?.value;
      const index = singleInput.value;
      const fromIndex = fromInput.value;
      const voz = vozSelect.value;
      const fonte = fonteSelect.value;

      let query = `scope=${scope}&voz=${voz}&fonte=${fonte}`;
      if (scope === "single" && index) query += `&single_index=${index}`;
      if (scope === "from" && fromIndex) query += `&from_index=${fromIndex}`;
      if (scope === "custom") {
        const lista = customInput.value.replace(/\s+/g, "");
        if (!lista.match(/^(\d+,)*\d+$/)) {
          alert("Formato inválido. Use apenas números separados por vírgula.");
          return;
        }
        query += `&custom_indices=${lista}`;
      }

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

        if (linha.includes("✅ Geração de narrações finalizada") || linha.includes("🔚 Fim do processo")) {
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
