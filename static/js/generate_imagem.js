document.addEventListener('DOMContentLoaded', () => {
  const list     = document.getElementById('image_list');
  const preview  = document.getElementById('preview_img');
  const radios   = document.querySelectorAll('input[name="scope"]');
  const singleIn = document.getElementById('single_index');
  const fromIn   = document.getElementById('from_index');
  const btn      = document.getElementById('generate_images');
  const barFill  = document.getElementById('progress_fill');
  const logArea  = document.getElementById('log');

  // Dê duplo clique para mostrar preview
  list.addEventListener('dblclick', () => {
    const idx = list.selectedIndex;
    if (idx < 0) return;
    const url = list.options[idx].dataset.url;
    if (url) preview.src = url;
  });

  // Habilita/desabilita inputs numéricos
  radios.forEach(radio => {
    radio.addEventListener('change', () => {
      singleIn.disabled = radio.value !== 'single';
      fromIn.disabled   = radio.value !== 'from';
    });
  });

    fetch('/imagens', {
    method: 'POST',
    body: data
  })
  .then(r => r.json())
  .then(json => {
    if (json.error) throw new Error(json.error);

    // 1) Atualiza o select com as cenas novas:
    const list = document.getElementById('image_list');
    list.innerHTML = '';  // limpa tudo
    json.cenas.forEach((cena, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = `Imagem ${idx+1} – ${cena.prompt_imagem}`;
      opt.dataset.url = `/static/imgs/imagem${idx+1}.jpg`;
      list.appendChild(opt);
    });

    // 2) Exibe o log passo a passo e atualiza progress bar:
    const logs = json.logs || [];
    logs.forEach((line, i) => {
      const pct = Math.round((i + 1) / logs.length * 100);
      barFill.style.width = pct + '%';
      logArea.textContent += line + '\n';
    });
  })
  .catch(err => {
    logArea.textContent += `❌ Erro: ${err.message}`;
  });


  btn.addEventListener('click', () => {
    const scope = document.querySelector('input[name="scope"]:checked').value;
    const data  = new URLSearchParams();
    data.append('scope', scope);
    if (scope === 'single') data.append('single_index', singleIn.value);
    if (scope === 'from')   data.append('from_index', fromIn.value);

    // Reseta UI
    barFill.style.width = '0%';
    logArea.textContent = '';

    // Mensagem inicial
    if (scope === 'all') {
      logArea.textContent += '👌 Ok, vou gerar todas as imagens\n';
    } else if (scope === 'single') {
      logArea.textContent += `👌 Ok, vou gerar a imagem ${singleIn.value}\n`;
    } else if (scope === 'from') {
      logArea.textContent += `👌 Ok, vou gerar as imagens a partir da ${fromIn.value}\n`;
    }

        // Preenchimento inicial para mostrar atividade
    barFill.style.width = '5%';

    // Chama o endpoint POST /imagens
    fetch('/imagens', {
      method: 'POST',
      body: data
    })
    .then(resp => resp.json())
    .then(json => {
      if (json.error) throw new Error(json.error);
      const logs = json.logs || [];
      logs.forEach((line, idx) => {
        const pct = Math.round((idx + 1) / logs.length * 100);
        barFill.style.width = pct + '%';
        logArea.textContent += line + '\n';
      });
    })
    .catch(err => {
      logArea.textContent += `❌ Erro: ${err.message}`;
    });
  });
});
