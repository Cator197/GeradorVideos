document.addEventListener('DOMContentLoaded', () => {
  const list     = document.getElementById('legenda_list');
  const radios   = document.querySelectorAll('input[name="scope"]');
  const singleIn = document.getElementById('single_index');
  const fromIn   = document.getElementById('from_index');
  const btn      = document.getElementById('generate_legendas');
  const barFill  = document.getElementById('progress_fill');
  const logArea  = document.getElementById('log');

  // Habilita/desabilita inputs numéricos
  radios.forEach(radio => {
    radio.addEventListener('change', () => {
      const selected = document.querySelector('input[name="scope"]:checked').value;
      singleIn.disabled = selected !== 'single';
      fromIn.disabled   = selected !== 'from';
    });
  });

  btn.addEventListener('click', () => {
    const scope = document.querySelector('input[name="scope"]:checked').value;
    const data  = new URLSearchParams();
    data.append('scope', scope);
    if (scope === 'single') data.append('single_index', singleIn.value);
    if (scope === 'from')   data.append('from_index', fromIn.value);

    barFill.style.width = '0%';
    logArea.textContent = '';

    if (scope === 'all') {
      logArea.textContent += '📝 Gerando todas as legendas\n';
    } else if (scope === 'single') {
      logArea.textContent += `📝 Gerando legenda ${singleIn.value}\n`;
    } else if (scope === 'from') {
      logArea.textContent += `📝 Gerando legendas a partir da ${fromIn.value}\n`;
    }

    barFill.style.width = '5%';

    fetch('/legendas', {
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
