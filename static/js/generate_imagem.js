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


  // ---- ADICIONAR IMAGEM (modal) ----
  const btnNova = document.getElementById('btn_nova_imagem');
  const modalAdd = document.getElementById('modal_add');
  const fecharAdd = document.getElementById('fechar_add');

  const tabGerar = document.getElementById('tab_gerar');
  const tabUpload = document.getElementById('tab_upload');
  const paneGerar = document.getElementById('pane_gerar');
  const paneUpload = document.getElementById('pane_upload');

  const gerarIndex = document.getElementById('gerar_index');
  const gerarNarr = document.getElementById('gerar_narracao');
  const gerarPrompt = document.getElementById('gerar_prompt');
  const btnCriarGerar = document.getElementById('btn_criar_gerar');

  const uploadIndex = document.getElementById('upload_index');
  const uploadNarr = document.getElementById('upload_narracao');
  const uploadArquivo = document.getElementById('upload_arquivo');
  const btnCriarUpload = document.getElementById('btn_criar_upload');

  // abrir/fechar
  if (btnNova) {
    btnNova.addEventListener('click', () => modalAdd.classList.remove('hidden'));
  }
  if (fecharAdd) {
    fecharAdd.addEventListener('click', () => modalAdd.classList.add('hidden'));
  }

  // tabs
  tabGerar?.addEventListener('click', () => {
    tabGerar.classList.add('border-blue-600');
    tabUpload.classList.remove('border-blue-600');
    paneGerar.classList.remove('hidden');
    paneUpload.classList.add('hidden');
  });
  tabUpload?.addEventListener('click', () => {
    tabUpload.classList.add('border-blue-600');
    tabGerar.classList.remove('border-blue-600');
    paneUpload.classList.remove('hidden');
    paneGerar.classList.add('hidden');
  });

  // alternância modo (gerar)
  document.querySelectorAll('input[name="modo_gerar"]').forEach(r => {
    r.addEventListener('change', () => {
      const ehNovo = document.querySelector('input[name="modo_gerar"]:checked').value === 'novo';
      gerarIndex.disabled = ehNovo;
      document.getElementById('grp_narracao_nova').classList.toggle('hidden', !ehNovo);
    });
  });

  // alternância modo (upload)
  document.querySelectorAll('input[name="modo_upload"]').forEach(r => {
    r.addEventListener('change', () => {
      const ehNovo = document.querySelector('input[name="modo_upload"]:checked').value === 'novo';
      uploadIndex.disabled = ehNovo;
      document.getElementById('grp_narracao_upload').classList.toggle('hidden', !ehNovo);
    });
  });

  // submit GERAR
  btnCriarGerar?.addEventListener('click', () => {
    const modo = document.querySelector('input[name="modo_gerar"]:checked').value;
    const payload = { modo, gerar_imagem: true };

    if (modo === 'novo') {
      payload.narracao = gerarNarr.value.trim();
      if (!payload.narracao) return alert('Informe a narração da nova cena.');
    } else {
      const idx = parseInt(gerarIndex.value, 10);
      if (!idx || idx < 1) return alert('Informe um índice válido.');
      payload.index = idx;
    }
    payload.prompt_imagem = gerarPrompt.value.trim();

    iniciarProgressoGenerico();
    fetch('/cenas/adicionar', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(resp => {
      pararProgressoGenerico();
      if (resp.status === 'ok') {
        modalAdd.classList.add('hidden');
        location.reload();
      } else {
        alert(resp.msg || 'Erro ao criar/gerar.');
      }
    })
    .catch(() => {
      pararProgressoGenerico();
      alert('Erro de rede ao criar/gerar.');
    });
  });

  // submit UPLOAD
  btnCriarUpload?.addEventListener('click', () => {
    const modo = document.querySelector('input[name="modo_upload"]:checked').value;
    const fd = new FormData();
    fd.append('modo', modo);

    if (modo === 'novo') {
      const narr = uploadNarr.value.trim();
      if (!narr) return alert('Informe a narração da nova cena.');
      fd.append('narracao', narr);
    } else {
      const idx = parseInt(uploadIndex.value, 10);
      if (!idx || idx < 1) return alert('Informe um índice válido.');
      fd.append('index', idx);
    }

    if (!uploadArquivo.files || !uploadArquivo.files[0]) {
      return alert('Selecione um arquivo.');
    }
    fd.append('arquivo', uploadArquivo.files[0]);

    iniciarProgressoGenerico();
    fetch('/cenas/adicionar_upload', {
      method: 'POST',
      body: fd
    })
    .then(r => r.json())
    .then(resp => {
      pararProgressoGenerico();
      if (resp.status === 'ok') {
        modalAdd.classList.add('hidden');
        location.reload();
      } else {
        alert(resp.msg || 'Erro ao criar/enviar.');
      }
    })
    .catch(() => {
      pararProgressoGenerico();
      alert('Erro de rede ao criar/enviar.');
    });
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
