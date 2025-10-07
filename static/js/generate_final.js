// static/js/generate_final.js
document.addEventListener('DOMContentLoaded', () => {
  /* ---------- HELPERS ---------- */
  const GHOST_SRC = document.body?.dataset?.logoGhost || "/static/img/ghost.png";
  const el = (html)=>{ const t=document.createElement("template"); t.innerHTML=html.trim(); return t.content.firstChild; };
  const clamp01 = (n)=>Math.max(0,Math.min(1,n));

  // Util: tenta extrair um pequeno preview de texto de legenda de um objeto de cena do backend
  const legendaPreviewFrom = (c) => {
    const t = c?.legenda || c?.narracao || c?.texto || c?.caption || c?.subtitle || "";
    const s = (Array.isArray(t) ? t.join(" ") : String(t||"")).trim();
    if (!s) return "(sem legenda)";
    return s.length > 100 ? s.slice(0, 97) + "..." : s;
  };

  const posToClass = (pos) => {
    switch (pos) {
      case "central": return "sub-pos-central";
      case "central-1": return "sub-pos-central-1";
      case "central-2": return "sub-pos-central-2";
      case "central-3": return "sub-pos-central-3";
      case "inferior":
      default: return "sub-pos-inferior";
    }
  };

  const svgCheck = `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7.8 13.6l-3-3a1 1 0 011.4-1.4l1.9 1.9 5.7-5.7a1 1 0 011.4 1.4l-7.1 7.1a1 1 0 01-1.4 0z"/></svg>`;
  const svgWarn  = `<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M10 2a1 1 0 01.9.55l7 14A1 1 0 0117 18H3a1 1 0 01-.9-1.45l7-14A1 1 0 0110 2zm0 5a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1zm0 8a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5z"/></svg>`;

  /* ---------- DATA ---------- */
  const listaTransicoes = [
    { value:"",           label:"Sem transição" },
    { value:"fade",       label:"Desvanecer (fade)" },
    { value:"wipeleft",   label:"Wipe esquerda" },
    { value:"wiperight",  label:"Wipe direita" },
    { value:"wipeup",     label:"Wipe cima" },
    { value:"wipedown",   label:"Wipe baixo" },
    { value:"slideleft",  label:"Slide esquerda" },
    { value:"slideright", label:"Slide direita" },
    { value:"slideup",    label:"Slide cima" },
    { value:"slidedown",  label:"Slide baixo" },
    { value:"circlecrop", label:"Crop circular" },
    { value:"rectcrop",   label:"Crop retângulo" },
    { value:"distance",   label:"Zoom afastando" },
    { value:"fadeblack",  label:"Fade preto" },
    { value:"fadewhite",  label:"Fade branco" },
    { value:"radial",     label:"Radial" },
    { value:"smoothleft", label:"Suave esquerda" },
    { value:"smoothright",label:"Suave direita" },
    { value:"smoothup",   label:"Suave cima" },
    { value:"smoothdown", label:"Suave baixo" },
    { value:"circleopen", label:"Abrir círculo" },
    { value:"circleclose",label:"Fechar círculo" },
    { value:"vertopen",   label:"Abrir vertical" },
    { value:"vertclose",  label:"Fechar vertical" },
    { value:"horzopen",   label:"Abrir horizontal" },
    { value:"horzclose",  label:"Fechar horizontal" },
    { value:"dissolve",   label:"Dissolver" },
    { value:"pixelize",   label:"Pixelizar" },
    { value:"diagtl",     label:"Diagonal TL" },
    { value:"diagtr",     label:"Diagonal TR" },
    { value:"diagbl",     label:"Diagonal BL" },
    { value:"diagbr",     label:"Diagonal BR" },
  ];
  const transLabelMap = Object.fromEntries(listaTransicoes.map(t=>[t.value, t.label]));

  const efeitos = [
    {value:"",                       label:"Nenhum"},
    {value:"zoom",                   label:"Zoom (Ken Burns)"},
    {value:"slide",                  label:"Slide"},
    {value:"tremor",                 label:"Tremor"},
    {value:"preto_branco",           label:"Preto e Branco"},
    {value:"espelho",                label:"Espelho"},
    {value:"escurecer",              label:"Escurecer"},
    {value:"blur_pulse",             label:"Desfoque Pulsante"},
    {value:"shake_horizontal",       label:"Tremor Horizontal"},
    {value:"shake_vertical",         label:"Tremor Vertical"},
    {value:"pulsar_brilho",          label:"Pulsar brilho"},
    {value:"cor_oscila",             label:"Cor oscila"},
    {value:"giro_leve",              label:"Giro leve"},
    {value:"loop_colorido",          label:"Loop colorido"},
    {value:"zoom_rapido_em_partes",  label:"Zoom rápido em partes"},
    {value:"distorcao_tv",           label:"Distorção TV"},
  ];
  const efeitoLabelMap = Object.fromEntries(efeitos.map(e=>[e.value, e.label]));

  /* ---------- DOM ---------- */
  const gridTrans          = document.getElementById("grid_transicoes");
  const gridEf             = document.getElementById("grid_efeitos");
  const checkboxLegendaG   = document.getElementById('checkbox_legenda_global');
  const selectPosicaoG     = document.getElementById('select_posicao_global');
  const selectTemplate     = document.getElementById('select_template');
  const btnGerarCenas      = document.getElementById('btn_gerar_cenas');
  const btnSalvarProjeto   = document.getElementById('btn_salvar_projeto');
  const btnVideo           = document.getElementById('btn_gerar_video');
  const barraIndeterminada = document.getElementById('barra_indeterminada');
  const logEl              = document.getElementById('log');

  // Escopo
  const scopeAllRadio      = document.getElementById('scope_all');
  const scopeSingleRadio   = document.getElementById('scope_single');
  const inputSingleIdx     = document.getElementById('input_single_idx');

  // Preview (direita)
  const previewPlayer      = document.getElementById("preview_player");
  const labelSlot          = document.getElementById("label_slot");
  const btnPrev            = document.getElementById("btn_prev");
  const btnNext            = document.getElementById("btn_next");
  const btnPreviewFull   = document.getElementById('btn_preview_full');

  // Trilha & Marca
  const trilhaCheckbox     = document.getElementById('usar_trilha');
  const trilhaInput        = document.getElementById('input_trilha');
  const configTrilha       = document.getElementById("config_trilha");
  const volumeSlider       = document.getElementById("volume_trilha");
  const volumeValor        = document.getElementById("volume_valor");
  const btnPreviewAudio    = document.getElementById("btn_preview_audio");
  const marcaCheckbox      = document.getElementById('usar_marca');
  const marcaInput         = document.getElementById('input_marca');
  const configMarca        = document.getElementById("config_marca");
  const opacidadeSlider    = document.getElementById("opacidade_marca");
  const opacidadeValor     = document.getElementById("opacidade_valor");

  const timelineInner      = document.getElementById("timeline_inner");

  /* ---------- STATE ---------- */
  const state = {
    scenes: [],                 // [{id, thumb, legenda, subtitleOn, posicao, efeito, intensidade(0..1), status:'nao'|'gerada'|'alterada', generating?:bool}]
    slots: [],                  // [{tipo, duracao}]
    selected: 0,
  };

  /* ---------- RENDER GRIDS (efeitos/transições) ---------- */
  efeitos.forEach(eff=>{
    const b = el(`
      <button class="btn-card btnfx btnfx--${eff.value || 'none'}" title="${eff.label}" aria-label="${eff.label}">
        <div class="demo-box">
          <img class="logo" src="${GHOST_SRC}" alt="logo efeito">
        </div>
        <span class="label">${eff.label}</span>
      </button>
    `);
    b.addEventListener("click", ()=>{
      const s = state.scenes[state.selected];
      if (!s) return;
      s.efeito = eff.value;
      if (s.status === 'gerada') s.status = 'alterada';
      renderTimeline(); atualizarPreview();
    });
    b.draggable = true;
    b.addEventListener("dragstart", e => e.dataTransfer.setData("tipo-efeito", eff.value));
    gridEf.appendChild(b);
  });

  listaTransicoes.forEach(t => {
    const cls = t.value ? t.value : 'none';
    const b = el(`
      <button class="btn-card btntr btntr--${cls}" title="${t.label}" aria-label="${t.label}">
        <div class="demo-box">
          <div class="layer a"><img class="logo" src="${GHOST_SRC}" alt="logo A"></div>
          <div class="layer b"><img class="logo" src="${GHOST_SRC}" alt="logo B"></div>
        </div>
        <span class="label">${t.label}</span>
      </button>
    `);
    b.draggable = true;
    b.addEventListener("dragstart", e => e.dataTransfer.setData("tipo-transicao", t.value));
    gridTrans.appendChild(b);
  });

  /* ---------- LOAD CENAS ---------- */
  async function carregarResumo() {
    try {
      const r = await fetch("/cenas/resumo");
      const j = await r.json();
      state.scenes = j.cenas.map(c => ({
        id: c.index0,
        thumb: c.media_url || null,
        legenda: legendaPreviewFrom(c),
        subtitleOn: true,
        posicao: "inferior",
        efeito: "",
        intensidade: 0.5,
        status: 'nao',      // nao | gerada | alterada
        generating: false,
      }));
      state.slots = Array(Math.max(0, state.scenes.length - 1)).fill(null)
                    .map(() => ({ tipo: "", duracao: 0.3 })); // default 0.3 quando tiver transição
      renderTimeline();
      atualizarPreview();
    } catch (e) { appendLog("❌ Erro ao carregar cenas: " + e.message); }
  }

  /* ---------- TIMELINE RENDER ---------- */
  function efeitoClass(val){ return val ? `eff-${val}` : ''; }

  function statusBadgeHTML(status){
    if (status === 'gerada')   return `<div class="status-badge status-gerada" title="Gerada">${svgCheck}</div>`;
    if (status === 'alterada') return `<div class="status-badge status-alterada" title="Alterada">${svgWarn}</div>`;
    return `<div class="status-badge status-nao" title="Não gerada"></div>`;
  }

  function setSlotVisual(slotEl, tipo, i){
    const labelEl = slotEl.querySelector(".label-vert");
    const durWrap = slotEl.querySelector(".slot-dur");
    if (tipo){
      slotEl.classList.add("slot-active");
      labelEl.textContent = transLabelMap[tipo] || tipo;

      // cria/atualiza controle de duração
      if (!durWrap) {
        const w = el(`
          <div class="slot-dur">
            <input class="slot-dur-input" type="number" step="0.1" min="0.1" />
          </div>
        `);
        slotEl.appendChild(w);
      }
      const input = slotEl.querySelector(".slot-dur-input");
      input.value = (state.slots[i]?.duracao ?? 0.3).toFixed(1);
      input.addEventListener("change", () => {
        const v = parseFloat(input.value || "0.3");
        state.slots[i].duracao = isNaN(v) ? 0.3 : Math.max(0.1, v);
      }, { once:true }); // reanexa quando recriar o slot
    }else{
      slotEl.classList.remove("slot-active");
      labelEl.textContent = "—";
      if (durWrap) durWrap.remove();
    }
  }

  function renderTimeline() {
    timelineInner.innerHTML = "";

    state.scenes.forEach((scene, i) => {
      const hasEff = !!scene.efeito;
      const intensityPercent = Math.round(scene.intensidade * 100);

      const card = el(`
        <div class="scene-card relative w-36 flex-shrink-0 border rounded-lg bg-white cursor-move ${scene.generating ? 'is-generating':''}" draggable="true" data-idx="${i}">
          <div class="text-center text-xs font-medium py-1 border-b bg-slate-50 relative">
            Cena ${i+1}
            <div class="absolute top-1 right-1">${statusBadgeHTML(scene.status)}</div>
          </div>

          <div class="scene-thumb aspect-[9/16] overflow-hidden flex items-center justify-center ${efeitoClass(scene.efeito)}"
               style="--fx-int:${scene.intensidade}; --fx-amp:4px;">
            ${scene.thumb ? `<img src="${scene.thumb}" alt="thumb cena ${i+1}">`
                           : `<div class="text-xs text-gray-400">sem mídia</div>`}
            ${scene.subtitleOn ? `
              <div class="subtitle-overlay ${posToClass(scene.posicao)}">
                <div class="subtitle-chip">${scene.legenda || "(sem legenda)"}</div>
              </div>` : ``}
          </div>

          <div class="p-2 space-y-2">
            <div class="flex items-center justify-between gap-2">
              <button class="btn-subtitle ${scene.subtitleOn ? 'on' : ''}" data-act="toggle-sub" data-idx="${i}">
                ${scene.subtitleOn ? 'Legenda ON' : 'Legenda OFF'}
              </button>
              <div class="effect-chip ${hasEff ? 'active' : ''}" data-act="clear-eff" data-idx="${i}" title="${hasEff ? (efeitoLabelMap[scene.efeito] || scene.efeito) : 'Sem efeito'}">
                ${hasEff ? (efeitoLabelMap[scene.efeito] || scene.efeito) : 'Sem efeito'}
              </div>
            </div>
            <input class="fx-intensidade w-full" type="range" min="0" max="100" value="${intensityPercent}" data-idx="${i}">
          </div>

          <div class="loading-overlay"><div class="spinner"></div></div>
        </div>
      `);

      // Drag: reordenar / aplicar efeito via drag
      card.addEventListener("dragstart", e => e.dataTransfer.setData("scene-from", i.toString()));
      card.addEventListener("dragover", e => e.preventDefault());
      card.addEventListener("drop", async e => {
        const ef = e.dataTransfer.getData("tipo-efeito");
        const from = e.dataTransfer.getData("scene-from");
        if (ef){
          state.scenes[i].efeito = ef;
          if (state.scenes[i].status === 'gerada') state.scenes[i].status = 'alterada';
          renderTimeline(); atualizarPreview(); return;
        }
        const f = parseInt(from,10);
        if (!Number.isNaN(f) && f !== i){
          moverCena(f, i); renderTimeline(); await persistirReordenacao(); atualizarPreview();
        }
      });

      // Selecionar cena
      card.addEventListener("click", () => { state.selected = i; atualizarPreview(); });

      timelineInner.appendChild(card);

      // Slot entre cenas
      if (i < state.scenes.length - 1) {
        const slot = el(`
          <div class="slot-vert flex-shrink-0">
            <div class="vbar"></div>
            <span class="label-vert">—</span>
          </div>
        `);
        setSlotVisual(slot, state.slots[i]?.tipo || "", i);

        slot.addEventListener("dragover", e => e.preventDefault());
        slot.addEventListener("drop", e => {
          const tipo = e.dataTransfer.getData("tipo-transicao");
          if (tipo === null || tipo === undefined) return;
          state.slots[i].tipo = tipo;
          // default inicial 0.3 ao inserir a transição
          state.slots[i].duracao = state.slots[i].duracao || 0.3;
          setSlotVisual(slot, tipo, i);
          atualizarPreview();
        });

        timelineInner.appendChild(slot);
      }
    });
  }

  // Delegação: controles do card
  timelineInner.addEventListener("click", (ev) => {
    const t = ev.target;
    // toggle legenda
    if (t && t.matches('[data-act="toggle-sub"]')) {
      const idx = parseInt(t.dataset.idx, 10);
      if (!Number.isNaN(idx) && state.scenes[idx]) {
        state.scenes[idx].subtitleOn = !state.scenes[idx].subtitleOn;
        if (state.scenes[idx].status === 'gerada') state.scenes[idx].status = 'alterada';
        renderTimeline();
      }
    }
    // limpar efeito
    if (t && t.matches('[data-act="clear-eff"]')) {
      const idx = parseInt(t.dataset.idx, 10);
      if (!Number.isNaN(idx) && state.scenes[idx]) {
        if (state.scenes[idx].efeito) {
          state.scenes[idx].efeito = "";
          if (state.scenes[idx].status === 'gerada') state.scenes[idx].status = 'alterada';
          renderTimeline();
        }
      }
    }
  });
  timelineInner.addEventListener("input", (ev) => {
    const t = ev.target;
    if (t && t.classList.contains('fx-intensidade')) {
      const idx = parseInt(t.dataset.idx, 10);
      if (!Number.isNaN(idx) && state.scenes[idx]) {
        state.scenes[idx].intensidade = clamp01(parseInt(t.value,10)/100);
        if (state.scenes[idx].status === 'gerada') state.scenes[idx].status = 'alterada';
        // atualizar só variáveis da thumb (sem re-render completo)
        const card = document.querySelector(`.scene-card[data-idx="${idx}"]`);
        const thumb = card?.querySelector('.scene-thumb');
        if (thumb) thumb.style.setProperty('--fx-int', state.scenes[idx].intensidade.toString());
        // também atualiza badge (alterada)
        if (card) {
          const badgeWrap = card.querySelector('.text-center .absolute');
          if (badgeWrap) badgeWrap.innerHTML = statusBadgeHTML(state.scenes[idx].status);
        }
      }
    }
  });

  function moverCena(from, to){
    const arr = state.scenes;
    const [m] = arr.splice(from,1); arr.splice(to,0,m);
    // recomputa slots (simples)
    state.slots = Array(Math.max(0, arr.length - 1)).fill(null).map(()=>({tipo:"", duracao:0.3}));
  }
  async function persistirReordenacao(){
    const new_order = state.scenes.map(s=>s.id);
    try{
      await fetch("/cenas/reordenar",{ method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({new_order})});
    }catch(e){ appendLog("⚠️ Falha ao persistir reordenação: " + e.message); }
  }

  /* ---------- PREVIEW DIREITO ---------- */
  function atualizarPreview(){
    const s = state.scenes[state.selected];
    if (previewPlayer) {
      const newSrc = `/preview_video/${state.selected}`;
      if (!previewPlayer.src.includes(newSrc)) {
        previewPlayer.src = newSrc;
        previewPlayer.load();
      }
    }
    const tipo = state.slots[state.selected]?.tipo || "";
    if (labelSlot) labelSlot.textContent = tipo ? (transLabelMap[tipo] || tipo) : "—";
  }

  function buildPreviewPayload() {
  return {
    order: state.scenes.map(s => s.id),
    scenes: state.scenes.map(s => ({
      efeito: s.efeito,
      intensidade: s.intensidade,     // 0..1
      subtitleOn: !!s.subtitleOn,
      posicao: s.posicao
    })),
    slots: state.slots.map(sl => ({
      tipo: sl.tipo || "",
      duracao: sl.duracao || 0.3
    })),
    trilha: {
      enabled: !!(trilhaCheckbox?.checked),
      volume: Number(volumeSlider?.value || 25)
    },
    marca: {
      enabled: !!(marcaCheckbox?.checked),
      opacidade: Number(opacidadeSlider?.value || 100)
    }
  };
}

async function previewFullVideo() {
  const payload = buildPreviewPayload();

  // UI: desabilita botão
  if (btnPreviewFull) {
    btnPreviewFull.disabled = true;
    const original = btnPreviewFull.textContent;
    btnPreviewFull.dataset._label = original;
    btnPreviewFull.textContent = "Gerando prévia…";
  }

  try {
    // Se o backend aceitar JSON puro (recomendado):
    let body; let headers;
    const precisaArquivos = (trilhaCheckbox?.checked && trilhaInput?.files?.[0]) ||
                            (marcaCheckbox?.checked  && marcaInput?.files?.[0]);

    if (!precisaArquivos) {
      headers = { "Content-Type": "application/json" };
      body = JSON.stringify(payload);
    } else {
      // Fallback: envia arquivos junto (o backend deve ler "payload" + files)
      const fd = new FormData();
      fd.append("payload", JSON.stringify(payload));
      if (trilhaCheckbox?.checked && trilhaInput?.files?.[0]) {
        fd.append("trilha", trilhaInput.files[0]);
      }
      if (marcaCheckbox?.checked && marcaInput?.files?.[0]) {
        fd.append("marca",  marcaInput.files[0]);
      }
      body = fd;
      headers = undefined;
    }

    const resp = await fetch("/preview_timeline", {
      method: "POST",
      headers,
      body
    });

    const json = await resp.json();
    if (!resp.ok || !json?.url) {
      throw new Error(json?.message || "Falha ao gerar a prévia.");
    }

    // Carrega e toca a prévia 360p
    if (previewPlayer) {
      previewPlayer.src = json.url;   // ex.: /cache/preview/<hash>.mp4
      previewPlayer.load();
      previewPlayer.play().catch(()=>{});
    }
  } catch (err) {
    alert("Erro ao gerar prévia do vídeo: " + err.message);
  } finally {
    // Restaura botão
    if (btnPreviewFull) {
      btnPreviewFull.disabled = false;
      btnPreviewFull.textContent = btnPreviewFull.dataset._label || "▶ Prévia do vídeo";
    }
  }
}

btnPreviewFull?.addEventListener("click", previewFullVideo);


  /* ---------- CONTROLES GLOBAIS ---------- */
  checkboxLegendaG?.addEventListener('change', e=>{
    const on = e.target.checked;
    state.scenes.forEach(s=> {
      if (s.subtitleOn !== on && s.status === 'gerada') s.status = 'alterada';
      s.subtitleOn = on;
    });
    renderTimeline();
  });
  selectPosicaoG?.addEventListener('change', e=>{
    const pos = e.target.value;
    state.scenes.forEach(s=>{
      if (s.posicao !== pos && s.status === 'gerada') s.status = 'alterada';
      s.posicao = pos;
    });
    renderTimeline();
  });
  selectTemplate?.addEventListener('change', e=>{
    const t = e.target.value;
    if (t === "suave"){
      state.scenes.forEach(s=> { if (s.status === 'gerada') s.status='alterada'; s.efeito = "zoom"; });
      state.slots.forEach(sl=>{ sl.tipo="fade"; sl.duracao = sl.duracao || 0.3; });
    } else if (t === "dinamico"){
      state.scenes.forEach((s,i)=> { if (s.status === 'gerada') s.status='alterada'; s.efeito = (i%2? "slide":"zoom"); });
      state.slots.forEach(sl=>{ sl.tipo="slideleft"; sl.duracao = sl.duracao || 0.3; });
    } else if (t === "semt"){
      state.scenes.forEach(s=> { if (s.status === 'gerada') s.status='alterada'; s.efeito = ""; });
      state.slots.forEach(sl=>{ sl.tipo=""; });
    }
    renderTimeline();
  });

  // Escopo radios
  [scopeAllRadio, scopeSingleRadio].forEach(r => r?.addEventListener('change', ()=>{
    inputSingleIdx.disabled = !scopeSingleRadio.checked;
  }));

  /* ---------- SALVAR / GERAR ---------- */
  async function salvarProjeto(){
    const cenasPayload = state.scenes.map(s=>({
      efeito: s.efeito,
      usarLegenda: !!s.subtitleOn,
      posicaoLegenda: s.posicao,
      config: { intensidade: s.intensidade }
    }));
    await fetch('/atualizar_config_cenas', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(cenasPayload) });
    alert("Projeto salvo.");
  }
  btnSalvarProjeto?.addEventListener("click", salvarProjeto);

  // Helpers: marcar spinner/badge
  function setGenerating(i, on){
    const card = document.querySelector(`.scene-card[data-idx="${i}"]`);
    if (!card) return;
    state.scenes[i].generating = !!on;
    card.classList.toggle('is-generating', !!on);
  }
  function setStatus(i, status){
    state.scenes[i].status = status;
    const card = document.querySelector(`.scene-card[data-idx="${i}"]`);
    if (!card) return;
    const badgeSpot = card.querySelector('.text-center .absolute');
    if (badgeSpot) badgeSpot.innerHTML = statusBadgeHTML(status);
  }

  btnGerarCenas?.addEventListener("click", async ()=>{
    // Determina escopo
    const scope = scopeSingleRadio?.checked ? "single" : "all";
    const singleIdx1 = parseInt(inputSingleIdx?.value || "0", 10);
    if (scope === "single" && (!singleIdx1 || singleIdx1 < 1 || singleIdx1 > state.scenes.length)) {
      alert("Informe um índice válido (1..N) para 'Apenas a cena'.");
      return;
    }

    // Persistir
    await salvarProjeto();

    // Spinner(s)
    if (scope === "all") {
      state.scenes.forEach((_,i)=> setGenerating(i, true));
    } else {
      setGenerating(singleIdx1-1, true);
    }

    // Checa .ass
    try {
      const resp = await fetch("/verificar_legendas_ass");
      const r = await resp.json();
      if (!r.tem) {
        alert("⚠️ Gere as legendas embutidas (.ass) antes de gerar as cenas.");
        if (scope === "all") state.scenes.forEach((_,i)=> setGenerating(i,false));
        else setGenerating(singleIdx1-1, false);
        return;
      }
    } catch (e) {
      appendLog("❌ Erro ao verificar legendas: " + e.message);
    }

    logEl.textContent=''; appendLog('🚧 Iniciando geração das cenas...');
    barraIndeterminada?.classList.remove("hidden");

    // Monta URL SSE
    let url = `/montar_cenas_stream?scope=${scope}`;
    if (scope === "single") url += `&single_index=${singleIdx1}`;

    const evtSource = new EventSource(url);

    evtSource.onmessage = (event) => {
      const msg = event.data || "";
      appendLog(msg);

      // heurística: tenta captar "Cena N" nas mensagens para ligar/desligar spinner por cena
      const m = msg.match(/cena\s*(\d+)/i);
      if (m) {
        const idx1 = parseInt(m[1], 10);
        if (!isNaN(idx1) && idx1 >= 1 && idx1 <= state.scenes.length) {
          // Se mensagem parece "iniciando", garante spinner ON
          if (/inici|gerando|montando/i.test(msg)) setGenerating(idx1-1, true);
          // Se parece "finalizada/concluída"
          if (/finalizad|conclu|pronta|ok/i.test(msg)) {
            setGenerating(idx1-1, false);
            setStatus(idx1-1, 'gerada');
          }
        }
      }

      if (msg.includes("🔚")) {
        // fallback: ao terminar stream, marca status por escopo
        if (scope === "all") {
          state.scenes.forEach((_,i)=> { setGenerating(i,false); setStatus(i,'gerada'); });
        } else {
          setGenerating(singleIdx1-1, false);
          setStatus(singleIdx1-1, 'gerada');
        }
        barraIndeterminada?.classList.add("hidden");
        evtSource.close();
      }
    };

    evtSource.onerror = () => {
      appendLog('❌ Erro na conexão de stream.');
      // desliga spinners
      if (scope === "all") state.scenes.forEach((_,i)=> setGenerating(i,false));
      else setGenerating(singleIdx1-1, false);
      barraIndeterminada?.classList.add("hidden");
      evtSource.close();
    };
  });

  btnVideo?.addEventListener("click", async ()=>{
    await salvarProjeto();

    const formData = new FormData();
    formData.append("escopo","all");
    formData.append("idx","");
    formData.append("transicoes", JSON.stringify(state.slots.map(sl=>({
      tipo: sl.tipo || "", duracao: sl.duracao || 0.3
    }))));

    if (trilhaCheckbox?.checked && trilhaInput?.files?.[0]){
      formData.append("usar_trilha","true");
      formData.append("trilha",trilhaInput.files[0]);
      formData.append("volume_trilha",volumeSlider.value);
    }
    if (marcaCheckbox?.checked && marcaInput?.files?.[0]){
      formData.append("usar_marca","true");
      formData.append("marca",marcaInput.files[0]);
      formData.append("opacidade_marca",opacidadeSlider.value);
    }

    appendLog('🚀 Iniciando geração...');
    barraIndeterminada?.classList.remove("hidden");

    fetch('/finalizar_stream', { method:'POST', body:formData })
      .then(r=>r.json())
      .then(data=>{
        barraIndeterminada?.classList.add("hidden");
        if (data.status==="ok"){
          appendLog('✅ Vídeo final gerado com sucesso');
          appendLog(data.output || "");
          if (previewPlayer){
            previewPlayer.src = `/video_final/${data.nome_arquivo}`;
            previewPlayer.load();
          }
        }else{
          appendLog('❌ Erro: ' + data.mensagem);
        }
      })
      .catch(err=>{
        appendLog('❌ Erro ao gerar vídeo final: ' + err.message);
        barraIndeterminada?.classList.add("hidden");
      });
  });

  /* ---------- TRILHA & MARCA ---------- */
  trilhaCheckbox?.addEventListener('change', ()=>{
    if (!trilhaInput) return;
    trilhaInput.disabled = !trilhaCheckbox.checked;
    configTrilha?.classList.toggle("hidden", !(trilhaCheckbox.checked && trilhaInput.files?.[0]));
  });
  trilhaInput?.addEventListener("change", ()=>{
    configTrilha?.classList.toggle("hidden", !(trilhaCheckbox?.checked && trilhaInput.files?.[0]));
  });
  volumeSlider?.addEventListener("input", ()=>{ if (volumeValor) volumeValor.textContent = `${volumeSlider.value}%`; });
  btnPreviewAudio?.addEventListener("click", ()=>{
    if (!trilhaInput?.files?.[0]){ alert("Selecione um arquivo de trilha sonora."); return; }
    const formData = new FormData(); formData.append("trilha",trilhaInput.files[0]); formData.append("volume",volumeSlider.value);
    appendLog("🎧 Gerando preview de áudio...");
    fetch("/preview_audio_trilha",{ method:"POST", body:formData })
      .then(resp=>resp.blob())
      .then(blob=>{ const url = URL.createObjectURL(blob); new Audio(url).play(); })
      .catch(err=> appendLog("❌ Erro no preview: " + err.message));
  });

  marcaCheckbox?.addEventListener('change', ()=>{
    if (!marcaInput) return;
    marcaInput.disabled = !marcaCheckbox.checked;
    configMarca?.classList.toggle("hidden", !(marcaCheckbox.checked && marcaInput.files?.[0]));
  });
  marcaInput?.addEventListener("change", ()=>{
    configMarca?.classList.toggle("hidden", !(marcaCheckbox?.checked && marcaInput.files?.[0]));
  });
  opacidadeSlider?.addEventListener("input", ()=>{ if (opacidadeValor) opacidadeValor.textContent = `${opacidadeSlider.value}%`; });

  /* ---------- LOG ---------- */
  function appendLog(msg) {
    if (!logEl) return;
    logEl.textContent += msg + '\n';
    logEl.scrollTop = logEl.scrollHeight;
  }

  /* ---------- INIT ---------- */
  carregarResumo();
});
