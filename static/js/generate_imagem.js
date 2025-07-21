document.addEventListener('DOMContentLoaded', () => {
  atualizarCreditosUI();
  const list       = document.getElementById('image_list');
  const barFill    = document.getElementById('progress_fill');
  const logArea    = document.getElementById('log');
  const btn        = document.getElementById('generate_images');
  const radios     = document.querySelectorAll('input[name="scope"]');
  const singleIn   = document.getElementById('single_index');
  const fromIn     = document.getElementById('from_index');
  const selectedInput = document.getElementById('selected_indices');

  // Modal de preview
  const modal         = document.getElementById('modal_preview');
  const modalImage    = document.getElementById('modal_image');
  const modalVideo    = document.getElementById('modal_video');
  const closeModal    = document.getElementById('close_modal');

  // Modal de edição
  const modalEdicao        = document.getElementById('modal_edicao');
  const fecharEdicao       = document.getElementById('fechar_edicao');
  const previewEdicao      = document.getElementById('preview_edicao');
  const previewVideoEdicao = document.getElementById('preview_video_edicao');
  const campoPrompt        = document.getElementById('campo_prompt_edicao');
  const btnSalvarPrompt    = document.getElementById('salvar_prompt');
  const btnSubstituirImagem = document.getElementById('substituir_imagem');
  const statusGeracao      = document.getElementById('status_geracao');
  const uploadInput        = document.getElementById('upload_imagem');
  const nomeArquivo        = document.getElementById('nome_arquivo');
  const previewUpload      = document.getElementById('preview_upload');

  let indiceSelecionado = null;

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

  function iniciarProgressoGenerico() {
  document.getElementById('barra_indeterminada').classList.remove('hidden');
}

  function pararProgressoGenerico() {
  document.getElementById('barra_indeterminada').classList.add('hidden');
}

  function mostrarMedia(url, imgEl, videoEl) {
    if (url?.endsWith(".mp4")) {
      imgEl.classList.add('hidden');
      videoEl.classList.remove('hidden');
      videoEl.src = url;
    } else if (url) {
      videoEl.classList.add('hidden');
      imgEl.classList.remove('hidden');
      imgEl.src = url;
    }
  }

  list.addEventListener('dblclick', () => {
    const idx = list.selectedIndex;
    if (idx < 0) return;
    const url = list.options[idx].dataset.url;
    if (url) {
      mostrarMedia(url, modalImage, modalVideo);
      modal.classList.remove('hidden');
    }
  });

  list.addEventListener('change', () => {
    const idx = list.selectedIndex;
    if (idx < 0) return;

    const opt = list.options[idx];
    indiceSelecionado = parseInt(opt.value);
    const prompt = opt.textContent.split('–')[1]?.trim();
    const url = opt.dataset.url;

    campoPrompt.value = prompt || '';
    mostrarMedia(url, previewEdicao, previewVideoEdicao);
    statusGeracao.classList.add('hidden');
    nomeArquivo.textContent = '';
    previewUpload.classList.add('hidden');
    modalEdicao.classList.remove('hidden');
  });

  closeModal.addEventListener('click', () => {
    modal.classList.add('hidden');
    modalImage.src = '';
    modalVideo.src = '';
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.classList.add('hidden');
      modalImage.src = '';
      modalVideo.src = '';
    }
  });

  fecharEdicao.addEventListener('click', () => {
    modalEdicao.classList.add('hidden');
    previewEdicao.src = '';
    previewVideoEdicao.src = '';
  });

  btnSalvarPrompt.addEventListener('click', () => {
    fetch('/editar_prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        index: indiceSelecionado,
        novo_prompt: campoPrompt.value
      })
    })
    .then(resp => resp.json())
    .then(data => {
      if (data.status === 'ok') {
        alert('✅ Prompt atualizado!');
        modalEdicao.classList.add('hidden');
        location.reload();
      }
    });
  });

  btnSubstituirImagem.addEventListener('click', () => {
    statusGeracao.classList.remove('hidden');
    fetch('/substituir_imagem', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        index: indiceSelecionado,
        novo_prompt: campoPrompt.value
      })
    })
    .then(resp => resp.json())
    .then(data => {
      statusGeracao.classList.add('hidden');
      if (data.status === 'ok') {
        alert('🔄 Imagem gerada com sucesso!');
        modalEdicao.classList.add('hidden');
        location.reload();
      }
    });
  });

  uploadInput.addEventListener('change', () => {
    const file = uploadInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('index', indiceSelecionado);
    formData.append('imagem', file);
    nomeArquivo.textContent = `📁 ${file.name}`;

    if (file.type.startsWith('image/')) {
      previewEdicao.src = URL.createObjectURL(file);
      previewEdicao.classList.remove('hidden');
      previewVideoEdicao.classList.add('hidden');
    } else if (file.type === 'video/mp4') {
      previewVideoEdicao.src = URL.createObjectURL(file);
      previewVideoEdicao.classList.remove('hidden');
      previewEdicao.classList.add('hidden');
    }

    fetch('/upload_imagem', {
      method: 'POST',
      body: formData
    })
    .then(resp => resp.json())
    .then(data => {
      if (data.status === 'ok') {
        alert('✅ Mídia substituída com sucesso!');
        modalEdicao.classList.add('hidden');
        location.reload();
      }
    });
  });

  radios.forEach(radio => {
    radio.addEventListener('change', () => {
      singleIn.disabled = radio.value !== 'single';
      fromIn.disabled   = radio.value !== 'from';
      selectedInput.classList.toggle('hidden', radio.value !== 'selected');
    });
  });

  btn.addEventListener('click', () => {
    const scope = document.querySelector('input[name="scope"]:checked').value;
    const data  = new URLSearchParams();
    data.append('scope', scope);

    if (scope === 'single') data.append('single_index', singleIn.value);
    if (scope === 'from')   data.append('from_index', fromIn.value);
    if (scope === 'selected') {
      const raw = selectedInput.value.trim();
      data.append('selected_indices', raw);
    }

    iniciarProgressoGenerico();
    logArea.textContent = '';

    if (scope === 'all') {
      logArea.textContent += '👌 Ok, vou gerar todas as imagens\n';
    } else if (scope === 'single') {
      logArea.textContent += `👌 Ok, vou gerar a imagem ${singleIn.value}\n`;
    } else if (scope === 'from') {
      logArea.textContent += `👌 Ok, vou gerar as imagens a partir da ${fromIn.value}\n`;
    } else if (scope === 'selected') {
      logArea.textContent += `👌 Ok, vou gerar as imagens selecionadas\n`;
    }

    const source = new EventSource('/imagens_stream?' + data.toString());
    let count = 0;

    source.onmessage = (event) => {
      const linha = event.data;
      logArea.textContent += linha + '\n';
      logArea.scrollTop = logArea.scrollHeight;


      if (linha.includes("finalizada")) {
        source.close();
        pararProgressoGenerico();
        atualizarCreditosUI();
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
      pararProgressoGenerico();
    };
  });
});
