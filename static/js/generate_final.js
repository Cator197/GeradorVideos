// static/js/generate_final.js

document.addEventListener('DOMContentLoaded', () => {
  const trilhaCheckbox    = document.getElementById('usar_trilha');
  const trilhaInput       = document.getElementById('input_trilha');
  const marcaCheckbox     = document.getElementById('usar_marca');
  const marcaInput        = document.getElementById('input_marca');
  const btnVideo          = document.getElementById('btn_gerar_video');
  const btnCapCut         = document.getElementById('btn_gerar_capcut');
  const progressBar       = document.getElementById('progress_fill');
  const logEl             = document.getElementById('log');
  const aplicarTodasCb    = document.getElementById('aplicar_todas');
  const sceneRows         = document.querySelectorAll('.scene-row');
  const modal             = document.getElementById('modal_preview_video');
  const previewVideo      = document.getElementById('preview_video');
  const previewSource     = document.getElementById('video_source');
  const closeModalBtn     = document.getElementById('close_modal_video');

  // Toggle file inputs
  trilhaCheckbox.addEventListener('change', () => trilhaInput.disabled = !trilhaCheckbox.checked);
  marcaCheckbox.addEventListener('change', () => marcaInput.disabled = !marcaCheckbox.checked);

  // Show/hide extra config for zoom effect
  function handleEfeitoChange(e) {
    const select = e.target;
    const row    = select.closest('.scene-row');
    const idx    = row.dataset.idx;
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

  // Aplicar efeito de primeira cena em todas, se marcado
  aplicarTodasCb.addEventListener('change', () => {
    if (!aplicarTodasCb.checked) return;
    const firstEfeito = document.querySelector('select[name="efeito_0"]').value;
    sceneRows.forEach(row => {
      const idx = row.dataset.idx;
      const sel = row.querySelector(`select[name="efeito_${idx}"]`);
      sel.value = firstEfeito;
      sel.dispatchEvent(new Event('change'));
    });
  });

  // Append log helper
  function appendLog(msg) {
    logEl.textContent += msg + '\n';
    logEl.scrollTop = logEl.scrollHeight;
  }

  // Collect scenes config
  function coletarCenas() {
    return Array.from(sceneRows).map(row => {
      const idx       = row.dataset.idx;
      const efeito    = row.querySelector(`select[name="efeito_${idx}"]`).value;
      const transicao = row.querySelector(`select[name="transicao_${idx}"]`)?.value || '';
      const duracao   = parseFloat(row.querySelector(`input[name="duracao_${idx}"]`)?.value) || 0.5;
      const config    = {};
      if (efeito === 'zoom') {
        config.fator = row.querySelector(`input[name="zoom_fator_${idx}"]`).value;
        config.modo  = row.querySelector(`select[name="zoom_tipo_${idx}"]`).value;
      }
      return { efeito, transicao, duracao, config };
    });
  }

  // Start SSE stream via POST
  async function startStream(payload) {
    appendLog('🚀 Iniciando geração...');
    const resp = await fetch('/finalizar_stream', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
    });
    if (!resp.ok) { appendLog(`❌ Erro HTTP ${resp.status}`); return; }

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer    = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream:true});
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      parts.forEach(part => {
        if (part.startsWith('data: ')) {
          const msg = part.replace(/^data: /, '').trim();
          appendLog(msg);
          if (/🎞️|✅/.test(msg)) {
            let cur = parseFloat(progressBar.style.width) || 0;
            progressBar.style.width = Math.min(cur + 10, 100) + '%';
          }
        }
      });
    }
    appendLog('✅ Finalização completa');
  }

  // Generate handler
  function gerar(tipo) {
    logEl.textContent = '';
    progressBar.style.width = '0%';
    appendLog('🧩 Coletando configurações...');
    const cenas = coletarCenas();
    appendLog(`🔧 ${cenas.length} cenas prontas`);
    const payload = { acao: tipo, cenas, usar_trilha: trilhaCheckbox.checked, usar_marca: marcaCheckbox.checked };
    if (trilhaCheckbox.checked && trilhaInput.files.length) payload.trilha_path = trilhaInput.files[0].name;
    if (marcaCheckbox.checked  && marcaInput.files.length ) payload.marca_path  = marcaInput.files[0].name;
    startStream(payload);
  }

  btnVideo.addEventListener('click', () => gerar('video'));
  btnCapCut.addEventListener('click', () => gerar('capcut'));

  // Preview double-click
  document.querySelectorAll('.scene-card').forEach(card => {
    card.addEventListener('dblclick', () => {
      const row = card.closest('.scene-row');
      previewSource.src = `/preview_video/${row.dataset.idx}`;
      modal.classList.remove('hidden');
      previewVideo.load();
    });
  });
  closeModalBtn.addEventListener('click', () => { modal.classList.add('hidden'); previewVideo.pause(); });
});
