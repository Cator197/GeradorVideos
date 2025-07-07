// Refatorado para usar barra indeterminada

// Inicializa quando DOM estiver pronto
document.addEventListener("DOMContentLoaded", () => {
  const lista = document.getElementById("narracao_list");
  const audio = document.getElementById("preview_audio");
  const source = document.getElementById("audio_source");
  const logArea = document.getElementById("log");
  const barraIndeterminada = document.getElementById("barra_indeterminada");

  const btnGerar = document.getElementById("generate_narracoes");
  const btnRemover = document.getElementById("remover_silencio");
  const silencioMin = document.getElementById("silencio_min");

  const editor = document.getElementById("editor_narracao");
  const textoBox = document.getElementById("texto_narracao");
  const btnSalvar = document.getElementById("salvar_narracao");

  const singleInput = document.getElementById("single_index");
  const fromInput = document.getElementById("from_index");
  const customInput = document.getElementById("custom_indices_narracao");

  const fonteSelect = document.getElementById("fonte");
  const vozSelect = document.getElementById("voz");
  const btnPreviewVoz = document.getElementById("preview_voz");

  let indiceSelecionado = null;

  const vozesPorFonte = {
    elevenlabs: [
      { value: "Adam", label: "Adam" },
      { value: "Alice", label: "Alice" },
      { value: "Antoni", label: "Antoni" },
      { value: "Aria", label: "Aria" },
      { value: "Arnold", label: "Arnold" },
      { value: "Bill", label: "Bill" },
      { value: "Brian", label: "Brian" },
      { value: "Callum", label: "Callum" },
      { value: "Charlie", label: "Charlie" },
      { value: "Charlotte", label: "Charlotte" },
      { value: "Chris", label: "Chris" },
      { value: "Clyde", label: "Clyde" },
      { value: "Daniel", label: "Daniel" },
      { value: "Dave", label: "Dave" },
      { value: "Domi", label: "Domi" },
      { value: "Dorothy", label: "Dorothy" },
      { value: "Drew", label: "Drew" },
      { value: "Elli", label: "Elli" },
      { value: "Emily", label: "Emily" },
      { value: "Eric", label: "Eric" },
      { value: "Ethan", label: "Ethan" },
      { value: "Fin", label: "Fin" },
      { value: "Freya", label: "Freya" },
      { value: "George", label: "George" },
      { value: "Gigi", label: "Gigi" },
      { value: "Giovanni", label: "Giovanni" },
      { value: "Glinda", label: "Glinda" },
      { value: "Grace", label: "Grace" },
      { value: "Harry", label: "Harry" },
      { value: "James", label: "James" },
      { value: "Jeremy", label: "Jeremy" },
      { value: "Jessica", label: "Jessica" },
      { value: "Jessie", label: "Jessie" },
      { value: "Joseph", label: "Joseph" },
      { value: "Josh", label: "Josh" },
      { value: "Laura", label: "Laura" },
      { value: "Liam", label: "Liam" },
      { value: "Lily", label: "Lily" },
      { value: "Matilda", label: "Matilda" },
      { value: "Michael", label: "Michael" },
      { value: "Mimi", label: "Mimi" },
      { value: "Nicole", label: "Nicole" },
      { value: "Patrick", label: "Patrick" },
      { value: "Paul", label: "Paul" },
      { value: "Rachel", label: "Rachel" },
      { value: "River", label: "River" },
      { value: "Roger", label: "Roger" },
      { value: "Sam", label: "Sam" },
      { value: "Sarah", label: "Sarah" },
      { value: "Serena", label: "Serena" },
      { value: "Thomas", label: "Thomas" },
      { value: "Will", label: "Will" },
      { value: "Papai Noel", label: "Papai Noel" }
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

  fonteSelect.addEventListener("change", () => atualizarVozes(fonteSelect.value));
  atualizarVozes(fonteSelect.value);

  btnPreviewVoz.addEventListener("click", () => {
    const fonte = fonteSelect.value;
    const voz = vozSelect.value;
    const path = `/static/vozes/${fonte}/${voz}.mp3`;
    new Audio(path).play().catch(() => alert("❌ Amostra de voz não encontrada."));
  });

  lista.addEventListener("dblclick", () => {
    const selected = lista.options[lista.selectedIndex];
    const url = selected?.dataset?.url;
    if (url) {
      source.src = url;
      audio.load();
      setTimeout(() => audio.play().catch(() => {}), 100);
    }
  });

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
        textoBox.value = data.texto || "";
        editor.classList.remove("hidden");
      })
      .catch(() => {
        textoBox.value = "";
        editor.classList.remove("hidden");
      });
  });

  btnSalvar.addEventListener("click", () => {
    const novoTexto = textoBox.value.trim();
    fetch("/editar_narracao", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: indiceSelecionado, novo_texto: novoTexto })
    })
      .then(resp => resp.json())
      .then(data => {
        if (data.status === "ok") {
          const msg = document.createElement("div");
          msg.textContent = "✅ Texto salvo com sucesso!";
          msg.className = "mt-2 text-green-600 font-semibold";
          editor.appendChild(msg);
          setTimeout(() => msg.remove(), 3000);
          lista.options[indiceSelecionado].textContent = `Narração ${indiceSelecionado + 1} – ${novoTexto.slice(0, 60)}${novoTexto.length > 60 ? "..." : ""}`;
        } else {
          alert("❌ Erro ao salvar.");
        }
      })
      .catch(() => alert("❌ Erro na comunicação com o servidor."));
  });

  document.querySelectorAll('input[name="scope"]').forEach(radio => {
    radio.addEventListener("change", () => {
      singleInput.disabled = radio.value !== "single";
      fromInput.disabled = radio.value !== "from";
      customInput.disabled = radio.value !== "custom";
    });
  });

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

      logArea.textContent = "🎤 Iniciando geração de narrações...\n";
      barraIndeterminada.classList.remove("hidden");

      const stream = new EventSource("/narracao_stream?" + query);
      stream.onmessage = (event) => {
        logArea.textContent += event.data + "\n";
        logArea.scrollTop = logArea.scrollHeight;

        if (event.data.includes("✅ Geração de narrações finalizada") || event.data.includes("🔚 Fim do processo")) {
          barraIndeterminada.classList.add("hidden");
          stream.close();
        }
      };
      stream.onerror = () => {
        logArea.textContent += "❌ Erro no servidor ou conexão encerrada.\n";
        barraIndeterminada.classList.add("hidden");
        stream.close();
      };
    });
  }

  if (btnRemover && silencioMin) {
    btnRemover.addEventListener("click", () => {
      const valor = silencioMin.value || "0.3";
      logArea.textContent += `🧹 Removendo silêncio com mínimo de ${valor}s...\n`;
      fetch(`/remover_silencio?min_silence=${valor}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.status === "ok") {
            logArea.textContent += `✅ Silências removidos de ${data.arquivos} arquivos.\n`;
          } else {
            logArea.textContent += `❌ Erro: ${data.error}\n`;
          }
        })
        .catch((err) => logArea.textContent += `❌ Erro na requisição: ${err}\n`);
    });
  }
});
