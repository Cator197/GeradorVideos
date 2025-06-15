document.addEventListener('DOMContentLoaded', () => {
  const list       = document.getElementById('final_list');
  const source     = document.getElementById('video_source');
  const preview    = document.getElementById('preview_video');
  const trilha     = document.getElementById('usar_trilha');
  const trilhaIn   = document.getElementById('input_trilha');
  const marca      = document.getElementById('usar_marca');
  const marcaIn    = document.getElementById('input_marca');
  const btnFinal   = document.getElementById('btn_gerar_video');
  const btnCap     = document.getElementById('btn_gerar_capcut');
  const barFill    = document.getElementById('progress_fill');
  const logArea    = document.getElementById('log');

  // Modal
  const modal      = document.getElementById('modal_preview_video');
  const closeModal = document.getElementById('close_modal_video');

  // Habilitar/desabilitar inputs de trilha e marca
  trilha.addEventListener('change', () => trilhaIn.disabled = !trilha.checked);
  marca.addEventListener('change', () => marcaIn.disabled = !marca.checked);

  // Preview do vídeo ao dar duplo clique
  list.addEventListener('dblclick', () => {
    const idx = list.selectedIndex;
    if (idx < 0) return;

    const videoUrl = `/preview_video/${idx + 1}`;
    source.src = videoUrl;
    preview.pause();
    preview.load();
    preview.play().catch(err => console.warn('Erro ao reproduzir vídeo:', err));

    if (modal) modal.classList.remove('hidden');
  });

  // Fechar modal (X)
  if (closeModal && modal) {
    closeModal.addEventListener('click', () => {
      modal.classList.add('hidden');
      preview.pause();
      source.src = '';
    });

    // Fechar clicando fora do conteúdo
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.add('hidden');
        preview.pause();
        source.src = '';
      }
    });
  }

  // Função para iniciar geração do vídeo final
  function gerarFinal(tipo) {
    const transicao = document.getElementById('transicao').value;

    const data = new URLSearchParams();
    data.append('acao', tipo);
    data.append('transicao', transicao);
    data.append('usar_trilha', trilha.checked ? 'true' : 'false');
    data.append('usar_marca', marca.checked ? 'true' : 'false');

    barFill.style.width = '0%';
    logArea.textContent = '🧩 Iniciando geração do vídeo final...\n';

    const source = new EventSource('/finalizar_stream?' + data.toString());
    let count = 0;

    source.onmessage = (event) => {
      const linha = event.data;
      logArea.textContent += linha + '\n';
      logArea.scrollTop = logArea.scrollHeight;

      if (linha.includes("cenas unidas") || linha.includes("salvo") || linha.includes("copiados")) {
        count++;
        const pct = Math.min(5 + count * 15, 100);
        barFill.style.width = pct + '%';
      }

      if (linha.includes("Finalização concluída")) {
        source.close();
      }
    };

    source.onerror = () => {
      logArea.textContent += "❌ Erro na conexão com o servidor.\n";
      source.close();
    };
  }

  // Botões
  btnFinal.addEventListener('click', () => gerarFinal('video'));
  btnCap.addEventListener('click', () => gerarFinal('capcut'));
});
