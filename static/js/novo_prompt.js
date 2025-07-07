document.addEventListener("DOMContentLoaded", () => {
  const btnProcessar = document.getElementById("processar_prompt_video");
  const btnAdicionarCena = document.getElementById("adicionar_cena");
  const campoNomeVideo = document.getElementById("nome_video_prompt");
  const listaCenas = document.getElementById("lista_cenas");

  const modal = document.getElementById("modal_prompt_formatado");
  const abrirModal = document.getElementById("abrir_modal_prompt_formatado");
  const fecharModal = document.getElementById("fechar_modal_prompt");
  const enviarPromptFormatado = document.getElementById("enviar_prompt_formatado");
  const campoPromptFormatado = document.getElementById("campo_prompt_formatado");

  let totalCenas = 1;

  // ➕ Adicionar nova cena
  btnAdicionarCena.addEventListener("click", () => {
    adicionarCena("", "");
  });

  // ✨ Processar Prompt criado manualmente
  btnProcessar.addEventListener("click", () => {
    const nomeVideo = campoNomeVideo.value.trim();
    if (!nomeVideo) {
      alert("❌ O nome do vídeo final não foi preenchido.");
      return;
    }

    const cenas = listaCenas.querySelectorAll(".cena");
    if (cenas.length === 0) {
      alert("❌ Nenhuma cena foi adicionada.");
      return;
    }

    let promptFinal = "";
    cenas.forEach((cena, index) => {
      const imagem = cena.querySelector(".campo-imagem").value.trim();
      const narracao = cena.querySelector(".campo-narracao").value.trim();

      if (imagem || narracao) {
        promptFinal += `Prompt${index + 1}\n`;
        if (imagem) promptFinal += `Imagem: ${imagem}\n`;
        if (narracao) promptFinal += `Narração: ${narracao}\n`;
        promptFinal += "---\n";
      }
    });

    if (!promptFinal.trim()) {
      alert("❌ Nenhum conteúdo válido nas cenas.");
      return;
    }

    enviarPromptParaServidor(promptFinal, nomeVideo);
  });

  // 📄 Enviar prompt formatado via modal
  enviarPromptFormatado.addEventListener("click", () => {
    const prompt = campoPromptFormatado.value.trim();
    const nomeVideo = campoNomeVideo.value.trim();

    if (!prompt) {
      alert("❌ O campo de prompt está vazio.");
      return;
    }
    if (!nomeVideo) {
      alert("❌ O nome do vídeo final não foi preenchido.");
      return;
    }

    enviarPromptParaServidor(prompt, nomeVideo);
    modal.classList.add("hidden");
  });

  // Abrir e fechar modal
  abrirModal.addEventListener("click", () => modal.classList.remove("hidden"));
  fecharModal.addEventListener("click", () => modal.classList.add("hidden"));

  // 🧠 Função para enviar prompt e processar
  function enviarPromptParaServidor(prompt, nomeVideo) {
    fetch("/processar_prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, nome_video: nomeVideo })
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === "ok") {
          alert("✅ Prompt processado e salvo com sucesso!");

          if (Array.isArray(data.cenas)) {
            // Preencher interface com cenas retornadas do parser
            listaCenas.innerHTML = "";
            totalCenas = 0;

            data.cenas.forEach(cena => {
              const imagem = cena.prompt_imagem || "";
              const narracao = cena.narracao || "";
              adicionarCena(imagem, narracao);
            });
          }
        } else {
          alert(`❌ Erro: ${data.error || "erro desconhecido."}`);
        }
      })
      .catch(err => {
        console.error("Erro ao enviar prompt:", err);
        alert("❌ Falha na comunicação com o servidor.");
      });
  }

  // 🧩 Função auxiliar para adicionar cena com valores
  function adicionarCena(imagem = "", narracao = "") {
    totalCenas += 1;
    const novaCena = document.createElement("div");
    novaCena.className = "cena bg-gray-50 p-4 rounded-lg shadow-sm space-y-4 border border-slate-200";
    novaCena.innerHTML = `
      <h3 class="font-semibold text-slate-800">Cena ${totalCenas}</h3>

      <div>
        <label class="block font-medium text-sm text-slate-700 mb-1">Imagem:</label>
        <input type="text" class="campo-imagem w-full p-2 border rounded shadow-sm" value="${imagem}" />
      </div>

      <div>
        <label class="block font-medium text-sm text-slate-700 mb-1">Narração:</label>
        <input type="text" class="campo-narracao w-full p-2 border rounded shadow-sm" value="${narracao}" />
      </div>
    `;
    listaCenas.appendChild(novaCena);
  }
});
