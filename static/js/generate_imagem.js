document.addEventListener('DOMContentLoaded', () => {
  const list       = document.getElementById('image_list');
  const preview    = document.getElementById('preview_img'); // usado apenas se quiser manter a versão antiga
  const barFill    = document.getElementById('progress_fill');
  const logArea    = document.getElementById('log');
  const btn        = document.getElementById('generate_images');
  const radios     = document.querySelectorAll('input[name="scope"]');
  const singleIn   = document.getElementById('single_index');
  const fromIn     = document.getElementById('from_index');

  // Modal preview
  const modal      = document.getElementById('modal_preview');
  const modalImage = document.getElementById('modal_image');
  const closeModal = document.getElementById('close_modal');

  // Abrir modal ao dar duplo clique na lista
  list.addEventListener('dblclick', () => {
    const idx = list.selectedIndex;
    if (idx < 0) return;
    const url = list.options[idx].dataset.url;
    if (url) {
      modalImage.src = url;
      modal.classList.remove('hidden');
    }
  });

  // Fechar modal com botão X
  closeModal.addEventListener('click', () => {
    modal.classList.add('hidden');
    modalImage.src = '';
  });

  // Fechar modal clicando fora
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.add('hidden');
      modalImage.src = '';
    }
  });

  // Habilitar/desabilitar campos
  radios.forEach(radio => {
    radio.addEventListener('change', () => {
      singleIn.disabled = radio.value !== 'single';
      fromIn.disabled   = radio.value !== 'from';
    });
  });

  // Gerar imagens
  btn.addEventListener('click', () => {
    const scope = document.querySelector('input[name="scope"]:checked').value;
    const data  = new URLSearchParams();
    data.append('scope', scope);
    if (scope === 'single') data.append('single_index', singleIn.value);
    if (scope === 'from')   data.append('from_index', fromIn.value);

    barFill.style.width = '0%';
    logArea.textContent = '';

    if (scope === 'all') {
      logArea.textContent += '👌 Ok, vou gerar todas as imagens\n';
    } else if (scope === 'single') {
      logArea.textContent += `👌 Ok, vou gerar a imagem ${singleIn.value}\n`;
    } else if (scope === 'from') {
      logArea.textContent += `👌 Ok, vou gerar as imagens a partir da ${fromIn.value}\n`;
    }

    const source = new EventSource('/imagens_stream?' + data.toString());
    let count = 0;

    source.onmessage = (event) => {
      const linha = event.data;
      logArea.textContent += linha + '\n';
      logArea.scrollTop = logArea.scrollHeight;

      if (linha.includes("salva em")) {
        count++;
        const total = list?.length || 10;
        const pct = Math.round((count / total) * 100);
        barFill.style.width = pct + '%';
      }

      if (linha.includes("finalizada")) {
        source.close();

        // Atualiza lista
        fetch("/imagens", { method: "GET" })
          .then(resp => resp.text())
          .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");
            const novaLista = doc.getElementById("image_list");
            if (novaLista) {
              list.innerHTML = novaLista.innerHTML;
            }
          });
      }
    };

    source.onerror = () => {
      logArea.textContent += "❌ Erro no servidor ou conexão encerrada.\n";
      source.close();
    };
  });
});
