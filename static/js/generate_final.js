document.addEventListener('DOMContentLoaded', () => {
  const list     = document.getElementById('final_list');
  const preview  = document.getElementById('preview_video');
  const source   = document.getElementById('video_source');
  const trilha   = document.getElementById('usar_trilha');
  const trilhaIn = document.getElementById('input_trilha');
  const marca    = document.getElementById('usar_marca');
  const marcaIn  = document.getElementById('input_marca');
  const btnFinal = document.getElementById('btn_gerar_video');
  const btnCap   = document.getElementById('btn_gerar_capcut');
  const barFill  = document.getElementById('progress_fill');
  const logArea  = document.getElementById('log');

  // Ativa/desativa campos
  trilha.addEventListener('change', () => trilhaIn.disabled = !trilha.checked);
  marca.addEventListener('change', () => marcaIn.disabled = !marca.checked);

  // Preview de vídeo ao dar duplo clique
  list.addEventListener('dblclick', () => {
    const idx = list.selectedIndex;
    if (idx < 0) return;
    const file = `/modules/videos_cenas/video${idx+1}.mp4`;
    source.src = file;
    preview.load();
    preview.play();
  });

  function gerarFinal(tipo) {
    const transicao = document.getElementById('transicao').value;
    const trilhaFile = trilhaIn.files[0];
    const marcaFile  = marcaIn.files[0];

    const data = new FormData();
    data.append('acao', tipo);
    data.append('transicao', transicao);
    data.append('usar_trilha', trilha.checked ? "true" : "false");
    data.append('usar_marca', marca.checked ? "true" : "false");
    if (trilha.checked && trilhaFile) data.append('trilha', trilhaFile);
    if (marca.checked && marcaFile)  data.append('marca', marcaFile);

    barFill.style.width = '0%';
    logArea.textContent = '🧩 Iniciando geração do vídeo final...\n';

    fetch('/finalizar', {
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
  }

  btnFinal.addEventListener('click', () => gerarFinal('video'));
  btnCap.addEventListener('click', () => gerarFinal('capcut'));
});

