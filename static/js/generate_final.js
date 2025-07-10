// static/js/generate_final.js

document.addEventListener('DOMContentLoaded', () => {
  const listaTransicoes = [
  { value: "", label: "Sem transição" },
  { value: "fade", label: "Desvanecer (fade)" },
  { value: "wipeleft", label: "Corte para a esquerda (wipeleft)" },
  { value: "wiperight", label: "Corte para a direita (wiperight)" },
  { value: "wipeup", label: "Corte para cima (wipeup)" },
  { value: "wipedown", label: "Corte para baixo (wipedown)" },
  { value: "slideleft", label: "Slide para a esquerda (slideleft)" },
  { value: "slideright", label: "Slide para a direita (slideright)" },
  { value: "slideup", label: "Slide para cima (slideup)" },
  { value: "slidedown", label: "Slide para baixo (slidedown)" },
  { value: "circlecrop", label: "Aparecer em círculo (circlecrop)" },
  { value: "rectcrop", label: "Aparecer em retângulo (rectcrop)" },
  { value: "distance", label: "Zoom afastando (distance)" },
  { value: "fadeblack", label: "Fade em preto (fadeblack)" },
  { value: "fadewhite", label: "Fade em branco (fadewhite)" },
  { value: "radial", label: "Radial (radial)" },
  { value: "smoothleft", label: "Deslizar suave esquerda (smoothleft)" },
  { value: "smoothright", label: "Deslizar suave direita (smoothright)" },
  { value: "smoothup", label: "Deslizar suave cima (smoothup)" },
  { value: "smoothdown", label: "Deslizar suave baixo (smoothdown)" },
  { value: "circleopen", label: "Abrir em círculo (circleopen)" },
  { value: "circleclose", label: "Fechar em círculo (circleclose)" },
  { value: "vertopen", label: "Abrir vertical (vertopen)" },
  { value: "vertclose", label: "Fechar vertical (vertclose)" },
  { value: "horzopen", label: "Abrir horizontal (horzopen)" },
  { value: "horzclose", label: "Fechar horizontal (horzclose)" },
  { value: "dissolve", label: "Dissolver (dissolve)" },
  { value: "pixelize", label: "Pixelizar (pixelize)" },
  { value: "diagtl", label: "Diagonal topo-esquerda (diagtl)" },
  { value: "diagtr", label: "Diagonal topo-direita (diagtr)" },
  { value: "diagbl", label: "Diagonal baixo-esquerda (diagbl)" },
  { value: "diagbr", label: "Diagonal baixo-direita (diagbr)" }
  ];

  const trilhaCheckbox      = document.getElementById('usar_trilha');
  const trilhaInput         = document.getElementById('input_trilha');
  const marcaCheckbox       = document.getElementById('usar_marca');
  const marcaInput          = document.getElementById('input_marca');
  const btnVideo            = document.getElementById('btn_gerar_video');
  const btnGerarCenas       = document.getElementById('btn_gerar_cenas');
  const barraIndeterminada  = document.getElementById('barra_indeterminada');
  const logEl               = document.getElementById('log');
  const sceneRows           = document.querySelectorAll('.scene-row');
  const modal               = document.getElementById('modal_preview_video');
  const previewVideo        = document.getElementById('preview_video');
  const previewSource       = document.getElementById('video_source');
  const closeModalBtn       = document.getElementById('close_modal_video');

  trilhaCheckbox.addEventListener('change', () => {
    trilhaInput.disabled = !trilhaCheckbox.checked;
  });

  marcaCheckbox.addEventListener('change', () => {
    marcaInput.disabled = !marcaCheckbox.checked;
  });

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

  // Adiciona dinamicamente o dropdown de transições
  const transicaoContainer = row.querySelector('.config-transicao');
  if (transicaoContainer) {
    const select = document.createElement('select');
    select.name = `transicao_${idx}`;
    select.className = "w-full border rounded text-xs px-2 py-1 mt-2";

    listaTransicoes.forEach(opt => {
      const option = document.createElement('option');
      option.value = opt.value;
      option.textContent = opt.label;
      select.appendChild(option);
    });

    transicaoContainer.innerHTML = `<label class="block text-xs text-gray-600">Transição:</label>`;
    transicaoContainer.appendChild(select);
  }

  // evento do efeito zoom
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
        config.fator = row.querySelector(`input[name="zoom_fator_${idx}"]`)?.value || '1.2';
        config.modo  = row.querySelector(`select[name="zoom_tipo_${idx}"]`)?.value || 'in';
      }

      return { efeito, transicao, duracao, config, usarLegenda, posicaoLegenda };
    });
  }

  function startStream(payload) {
    appendLog('🚀 Iniciando geração...');
    barraIndeterminada?.classList.remove("hidden");

    fetch('/finalizar_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(resp => {
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp.json();
    })
    .then(data => {
      barraIndeterminada?.classList.add("hidden");
      if (data.status === "ok") {
        appendLog('✅ Vídeo final gerado com sucesso');
        appendLog(data.output);
      } else {
        appendLog('❌ Erro: ' + data.mensagem);
      }
    })
    .catch(err => {
      appendLog('❌ Erro ao gerar vídeo final: ' + err.message);
      barraIndeterminada?.classList.add("hidden");
    });
  }

  document.querySelectorAll('input[name="scope_cena"]').forEach(radio => {
    radio.addEventListener('change', () => {
      const single = document.querySelector('input[name="scope_cena"][value="single"]').checked;
      document.getElementById('input_single_idx').disabled = !single;
    });
  });

  btnGerarCenas.addEventListener('click', async () => {
    const escopo = document.querySelector('input[name="scope_cena"]:checked').value;
    const input  = document.getElementById('input_single_idx');
    const indice = parseInt(input.value);

    if (escopo === 'single' && (isNaN(indice) || indice < 1)) {
      alert('Informe um número de cena válido.');
      return;
    }

    await fetch('/atualizar_config_cenas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(coletarCenas())
    });

    logEl.textContent = '';
    appendLog('🚧 Iniciando geração das cenas...');
    barraIndeterminada?.classList.remove("hidden");

    let url = `/montar_cenas_stream?scope=${escopo}`;
    if (escopo === 'single') url += `&single_index=${indice}`;

    const evtSource = new EventSource(url);

    evtSource.onmessage = (event) => {
      appendLog(event.data);
      if (event.data.includes("🔚")) {
        barraIndeterminada?.classList.add("hidden");
        evtSource.close();
      }
    };

    evtSource.onerror = () => {
      appendLog('❌ Erro na conexão de stream.');
      barraIndeterminada?.classList.add("hidden");
      evtSource.close();
    };
  });

  btnVideo.addEventListener('click', () => {
    const cenas = coletarCenas();
    const escopo = document.querySelector('input[name="scope_cena"]:checked').value;
    const inputIdx = document.getElementById('input_single_idx').value;

    const payload = {
      escopo,
      trilha: trilhaCheckbox.checked ? trilhaInput.files[0]?.name : null,
      marca: marcaCheckbox.checked ? marcaInput.files[0]?.name : null,
      idx: inputIdx,
      transicoes: cenas.slice(0, -1).map(cena => ({
        tipo: cena.transicao,
        duracao: cena.duracao
      }))
    };

    startStream(payload);
  });

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
