document.addEventListener("DOMContentLoaded", () => {
  atualizarCreditosUI();
});

function atualizarCreditosUI() {
  fetch("/api/creditos")
    .then(res => res.json())
    .then(data => {
      const el = document.getElementById("creditos_valor");
      if (el) el.textContent = data.creditos;
    })
    .catch(() => {
      console.warn("⚠️ Não foi possível atualizar os créditos.");
    });
}
