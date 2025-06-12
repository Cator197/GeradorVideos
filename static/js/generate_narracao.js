document.addEventListener('DOMContentLoaded', () => {
  const list     = document.getElementById('narracao_list');
  const audio    = document.getElementById('preview_audio');
  const audioSrc = document.getElementById('audio_source');
  const radios   = document.querySelectorAll('input[name="scope"]');
  const singleIn = document.getElementById('single_index');
  const fromIn   = document.getElementById('from_index');
  const btn      = document.getElementById('generate_narracoes');
  const barFill  = document.getElementById('progress_fill');
  const logArea  = document.getElementById('log');

  // Duplo clique para tocar narração
  list.addEventListener('dblclick', () => {
    const idx = list.selectedIndex;
    if (idx < 0) return;
    const file = `/modules/audios_narracoes/narracao${idx+1}.mp3`;
    audioSrc.src = file;
    audio.load();
    audio.play();
  });

  // Habilita/desabilita inputs numéricos
  radios.forEach(radio => {
    radio.addEventListener('change', () => {
      singleIn.disabled = radio.value !== 'single';
      fromIn.disabled   = radio.value !== 'from';
    });
  });

  btn.addEventListener('click', () => {
    const scope = document.querySelector('input[name="scope"]:checked').value;
    const fonte = document.getElementById('fonte').value;
    const data  = new URLSearchParams();
    data.append('scope', scope);
    data.append('fonte', fonte);
    if (scope === 'single') data.append('single_index', singleIn.value);
    if (scope === 'from')   data.append('from_index', fromIn.value);

    barFill.style.width = '0%';
    logArea.textContent = '';

    if (scope === 'all') {
      logArea.textContent += '🎙️ Ok, vou gerar todas as narrações\n';
    } else if (scope === 'single') {
      logArea.textContent += `🎙️ Ok, vou gerar a narração ${singleIn.value}\n`;
    } else if (scope === 'from') {
      logArea.textContent += `🎙️ Ok, vou gerar as narrações a partir da ${fromIn.value}\n`;
    }

    barFill.style.width = '5%';

    fetch('/narracoes', {
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
