document.addEventListener('DOMContentLoaded', () => {
  const trilhaCheckbox = document.getElementById('usar_trilha');
  const trilhaInput = document.getElementById('input_trilha');
  const marcaCheckbox = document.getElementById('usar_marca');
  const marcaInput = document.getElementById('input_marca');
  const btnVideo = document.getElementById('btn_gerar_video');
  const barraIndeterminada = document.getElementById('barra_indeterminada');
  const logEl = document.getElementById('log');
  const sceneRows = document.querySelectorAll('.scene-row');
  const modal = document.getElementById('modal_preview_video');
  const previewVideo = document.getElementById('preview_video');
  const previewSource = document.getElementById('video_source');
  const closeModalBtn = document.getElementById('close_modal_video');

  trilhaCheckbox.addEventListener('change', () => trilhaInput.disabled = !trilhaCheckbox.checked);
  marcaCheckbox.addEventListener('change', () => marcaInput.disabled = !marcaCheckbox.checked);

  function handleEfeitoChange(e) {
    const select = e.target;
    const row = select.closest('.scene-row');
    const idx = row.dataset.idx;
    const container = row.querySelector('.config-efeito');
    if (select.value === 'zoom') {
      container.innerHTML = `
        <label class="block text-xs text-gray-600 mt-2">Fator de Zoom:</label>
        <input type="number" min="1" max="3" step="0.1" value="1.2" name="zoom_fator_${idx}" class="w-full border rounded text-xs px-2 py-1">
        <label class="block text-xs text-gray-600 mt-2">Tipo:</label>
        <select name="zoom_tipo_${idx}" class="w-full border rounded text-xs px-2 py-1">
          <option value="in">Aproximar</option>
          <option value="out">Afastar</option>
        </select>
      `;
      container.classList.remove('hidden');
    } else {
      container.innerHTML = '';
      container.classList.add('hidden');
    }
  }

  sceneRows.forEach(row => {
    const idx = row.dataset.idx;
    const sel = row.querySelector(`select[name="efeito_${idx}"]`);
    sel.addEventListener('change', handleEfeitoChange);
  });

  function appendLog(msg) {
    logEl.textContent += msg + '\n';
    logEl.scrollTop = logEl.scrollHeight;
  }

  function coletarCenas() {
    return Array.from(sceneRows).map(row => {
      const idx = row.dataset.idx;
      const efeito = row.querySelector(`select[name="efeito_${idx}"]`).value;
      const transicao = row.querySelector(`select[name="transicao_${idx}"]`)?.value || '';
      const duracao = parseFloat(row.querySelector(`input[name="duracao_${idx}"]`)?.value) || 0.5;

      const usarLegenda = row.querySelector(`input[name="usar_legenda_${idx}"]`)?.checked || false;
      const posicaoLegenda = row.querySelector(`select[name="posicao_legenda_${idx}"]`)?.value || 'inferior';

      const config = {};
      if (efeito === 'zoom') {
        config.fator = row.querySelector(`input[name="zoom_fator_${idx}"]`).value;
        config.modo = row.querySelector(`select[name="zoom_tipo_${idx}"]`).value;
      }

      return { efeito, transicao, duracao, config, usarLegenda, posicaoLegenda };
    });
  }

  async function startStream(payload) {
    appendLog('🚀 Iniciando geração...');
    barraIndeterminada?.classList.remove("hidden");

    const resp = await fetch('/finalizar_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      appendLog(`❌ Erro HTTP ${resp.status}`);
      barraIndeterminada?.classList.add("hidden");
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      parts.forEach(part => {
        if (part.startsWith('data: ')) {
          const msg = part.replace(/^data: /, '').trim();
          appendLog(msg);
        }
      });
    }

    barraIndeterminada?.classList.add("hidden");
    appendLog('✅ Finalização completa');
  }

  // Habilita ou desabilita o campo de número da cena
    document.querySelectorAll('input[name="scope_cena"]').forEach(radio => {
      radio.addEventListener('change', () => {
        const single = document.querySelector('input[name="scope_cena"][value="single"]').checked;
        document.getElementById('input_single_idx').disabled = !single;
      });
    });

    // Clique no botão de gerar cenas (lógica real será implementada depois)
    document.getElementById('btn_gerar_cenas').addEventListener('click', () => {
      const escopo = document.querySelector('input[name="scope_cena"]:checked').value;
      const input = document.getElementById('input_single_idx');
      const indice = parseInt(input.value);

      if (escopo === 'single' && (isNaN(indice) || indice < 1)) {
        alert('Informe um número de cena válido.');
        return;
      }

      console.log("🔧 Gerar cenas:", escopo === 'all' ? 'todas' : `cena ${indice}`);
      // Chamada AJAX para gerar cenas virá aqui...
    });


  function gerar(tipo) {
    logEl.textContent = '';
    appendLog('🧩 Coletando configurações...');
    const cenas = coletarCenas();
    appendLog(`🔧 ${cenas.length} cenas prontas`);

    const payload = {
      acao: tipo,
      cenas,
      usar_trilha: trilhaCheckbox.checked,
      usar_marca: marcaCheckbox.checked
    };

    if (trilhaCheckbox.checked && trilhaInput.files.length)
      payload.trilha_path = trilhaInput.files[0].name;

    if (marcaCheckbox.checked && marcaInput.files.length)
      payload.marca_path = marcaInput.files[0].name;

    startStream(payload);
  }

  btnVideo.addEventListener('click', () => gerar('video'));

  // Dê duplo clique em uma cena para pré-visualizar
  document.querySelectorAll('.scene-card').forEach(card => {
    card.addEventListener('dblclick', () => {
      const row = card.closest('.scene-row');
      previewSource.src = `/preview_video/${row.dataset.idx}`;
      modal.classList.remove('hidden');
      previewVideo.load();
    });
  });

  closeModalBtn.addEventListener('click', () => {
    modal.classList.add('hidden');
    previewVideo.pause();
  });
});
