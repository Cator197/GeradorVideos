document.addEventListener("DOMContentLoaded", () => {
  const btnProcessar = document.getElementById("processar_prompt_video");
  const campoPrompt = document.getElementById("initial_prompt_video");
  const campoNomeVideo = document.getElementById("nome_video_prompt");

  btnProcessar.addEventListener("click", () => {
    const prompt = campoPrompt.value.trim();
    const nomeVideo = campoNomeVideo.value.trim();

    if (!prompt) {
      alert("❌ O campo de prompt está vazio.");
      return;
    }

    if (!nomeVideo) {
      alert("❌ O nome do vídeo final não foi preenchido.");
      return;
    }

    fetch("/processar_prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        nome_video: nomeVideo
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === "ok") {
          alert("✅ Prompt processado e salvo com sucesso!");
        } else {
          alert(`❌ Erro: ${data.error || "erro desconhecido."}`);
        }
      })
      .catch(err => {
        console.error("Erro ao enviar prompt:", err);
        alert("❌ Falha na comunicação com o servidor.");
      });
  });
});
