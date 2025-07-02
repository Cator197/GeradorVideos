document.addEventListener("DOMContentLoaded", () => {
  const btnNovoPrompt = document.getElementById("novo-prompt");
  const modal = document.getElementById("modal_novo_prompt");
  const confirmar = document.getElementById("confirmar_novo_prompt");
  const cancelar = document.getElementById("cancelar_novo_prompt");

  if (btnNovoPrompt && modal && confirmar && cancelar) {
    btnNovoPrompt.addEventListener("click", () => {
      modal.classList.remove("hidden");
    });

    confirmar.addEventListener("click", () => {
      window.location.href = "/generate_prompt";
    });

    cancelar.addEventListener("click", () => {
      modal.classList.add("hidden");
    });
  }
});
