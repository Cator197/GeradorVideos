document.addEventListener('DOMContentLoaded', () => {
  const radios   = document.querySelectorAll('input[name="scope"]');
  const singleIn = document.getElementById('single_index');
  const fromIn   = document.getElementById('from_index');
  const btn      = document.getElementById('generate_montagem');
  const barFill  = document.getElementById('progress_fill');
  const logArea  = document.getElementById('log');

  // Ativa/desativa inputs numéricos conforme seleção
  radios.forEach(radio => {
    radio.addEventListener('change', () => {
      const selected = document.querySelector('input[name="scope"]:checked').value;
      singleIn.disabled = selected !== 'single';
      fromIn.disabled   = selected !== 'from';
    });
  });

  btn.addEventListener('click', () => {
    const scope   = document.querySelector('input[name="scope"]:checked').value;
    const tipo    = document.getElementById('tipo').value;
    const cor     = document.getElementById('cor').value;
    const tamanho = document.getElementById('tamanho').value;
    const posicao = document.getElementById('posicao').value;

    const data = new URLSearchParams();
    data.append('scope', scope);
    data.append('tipo', tipo);
    data.append('cor', cor);
    data.append('tamanho', tamanho);
    data.append('posicao', posicao);

    if (scope === 'single') data.append('single_index', singleIn.value);
    if (scope === 'from')   data.append('from_index', fromIn.value);

    barFill.style.width = '0%';
    logArea.textContent = '';

    if (scope === 'all') {
      logArea.textContent += '🧩 Montando todas as cenas\n';
    } else if (scope === 'single') {
      logArea.textContent += `🧩 Montando cena ${singleIn.value}\n`;
    } else if (scope === 'from') {
      logArea.textContent += `🧩 Montando cenas a partir da ${fromIn.value}\n`;
    }

    const source = new EventSource('/montagem_stream?' + data.toString());
    let count = 0;

    source.onmessage = (event) => {
      const linha = event.data;
      logArea.textContent += linha + '\n';
      logArea.scrollTop = logArea.scrollHeight;

      if (
        linha.includes("Criando vídeo base") ||
        linha.includes("gerada") ||
        linha.includes("Embutindo")
      ) {
        count++;
        const total = document.getElementById("narracao_list")?.length || 10;
        const pct = Math.round((count / total) * 100);
        barFill.style.width = pct + '%';
      }

      if (linha.includes("Fim do processo")) {
        source.close();
      }
    };

    source.onerror = () => {
      logArea.textContent += "❌ Erro no servidor ou conexão encerrada.\n";
      source.close();
    };
  });
});
