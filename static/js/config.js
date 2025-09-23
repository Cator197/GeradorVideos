document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('form_config');
  const pastaInput = document.getElementById('pasta_salvar');
  const btnEscolherPasta = document.getElementById('btn_escolher_pasta');
  const uploadInput = document.getElementById('upload_config');
  const btnEnviar = document.getElementById('btn_enviar_config');

  // Carregar configurações salvas
  fetch('/api/configuracoes')
    .then(res => res.json())
    .then(data => {

      document.getElementById('eleven_email').value = data.eleven_email || '';
      document.getElementById('eleven_senha').value = data.eleven_senha || '';
      pastaInput.value = data.pasta_salvar || '';
    });

  // Botão para escolher pasta (via backend)
  btnEscolherPasta.addEventListener('click', () => {
    fetch('/selecionar_pasta')
      .then(res => res.json())
      .then(data => {
        if (data.pasta) {
          pastaInput.value = data.pasta;
        } else {
          alert('❌ Erro ao selecionar a pasta.');
        }
      })
      .catch(() => alert('❌ Erro na comunicação com o servidor.'));
  });

  // Enviar configurações ao servidor
  form.addEventListener('submit', (e) => {
    e.preventDefault();

    const configData = {

      eleven_email: document.getElementById('eleven_email').value,
      eleven_senha: document.getElementById('eleven_senha').value,
      pasta_salvar: pastaInput.value
    };

    fetch('/salvar_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(configData)
    })
      .then(res => res.json())
      .then(data => {
        console.log("📥 Resposta do servidor:", data);
        if (data.status === 'ok') {
          alert('✅ Configurações salvas com sucesso!');
        } else {
          alert('❌ Erro ao salvar configurações.');
        }
      })
      .catch(() => alert('❌ Falha ao enviar configurações.'));
  });

  btnEnviar.addEventListener('click', () => {
  const file = uploadInput.files[0];
  if (!file) { alert("❌ Nenhum arquivo selecionado."); return; }
  // checar extensão
  if (!file.name.endsWith(".crd")) {
    alert("❌ Selecione um arquivo .crd (pacote de crédito).");
    return;
  }
  const formData = new FormData();
  formData.append("arquivo", file);
  fetch("/upload_credit_pack", {
    method: "POST",
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.status === 'ok') {
      alert("✅ Pacote aplicado com sucesso: " + data.mensagem);
      atualizarCreditosUI();
    } else {
      alert("❌ Erro: " + data.mensagem);
    }
  })
  .catch(() => { alert("❌ Erro na comunicação com o servidor."); });
});


});
