// filepath: c:\Users\Dev\robo\robo\app\static\js\emuladores.js
// ====== DUPLICAÇÃO (opcional) ======
(() => {
  const form = document.getElementById("formDuplicar");
  if (!form) return;

  const btn = document.getElementById("btnDuplicar");
  const spinner = document.getElementById("spinnerDuplicar");
  const label = document.getElementById("labelBtnDuplicar");
  const alerta = document.getElementById("alertaDuplicacao");
  const modalEl = document.getElementById("modalDuplicacao");
  const statusEl = document.getElementById("statusDuplicacao");
  const resultadoEl = document.getElementById("resultadoDuplicacao");
  const modal = new bootstrap.Modal(modalEl);

  function setLoading(on) {
    spinner.classList.toggle("d-none", !on);
    btn.disabled = on;
    label.textContent = on ? "Aguarde..." : "Duplicar";
  }
  const alertHtml = (kind, msg) => `<div class="alert alert-${kind} p-2 mb-0">${msg}</div>`;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.innerHTML = "";
    resultadoEl.classList.add("d-none");
    statusEl.textContent = "Iniciando...";
    modal.show();
    setLoading(true);
    try {
      const fd = new FormData(form);
      const res = await fetch("/duplicar_avd", { method: "POST", body: fd });
      const j = await res.json();
      if (!res.ok || j.erro) throw new Error(j.erro || "Falha");
      const { task_id } = j;
      const intv = setInterval(async () => {
        try {
          const r = await fetch(`/status/${task_id}`).then(r => r.json());
            if (r.erro) throw new Error(r.erro);
          if (r.status === "concluido") {
            clearInterval(intv);
            resultadoEl.classList.remove("d-none");
            resultadoEl.innerHTML = alertHtml("success", "Concluído!");
            setLoading(false);
            setTimeout(()=>location.reload(), 1200);
          } else {
            statusEl.textContent = `Status: ${r.status}`;
          }
        } catch (err) {
          clearInterval(intv);
          resultadoEl.classList.remove("d-none");
          resultadoEl.innerHTML = alertHtml("danger", err.message || err);
          setLoading(false);
        }
      }, 1000);
    } catch (err) {
      setLoading(false);
      alerta.innerHTML = alertHtml("danger", err.message || err);
    }
  });
})();

// ====== START / STOP POLL ======
(() => {
  const banner = document.getElementById("startBusyBanner");

  function setStartBusy(busy) {
    banner.classList.toggle("d-none", !busy);
    document.querySelectorAll(".btn-ligar, .btn-ligar-all").forEach(b=>{
      b.disabled = busy;
      const sp = b.querySelector(".spinner-border");
      if (sp) sp.classList.toggle("d-none", !busy);
    });
  }

  let prev = false;
  async function poll() {
    try {
      const { busy } = await fetch("/status/start_busy", {cache:"no-store"}).then(r=>r.json());
      setStartBusy(busy);
      if (prev && !busy) location.reload();
      prev = busy;
    } catch {}
  }
  poll();
  setInterval(poll, 1500);

  // Ligar: mostra busy imediatamente
  document.querySelectorAll("form.form-ligar, form[action='/ligar_todos']").forEach(f=>{
    f.addEventListener("submit", ()=> setStartBusy(true));
  });
})();

// ====== DESLIGAR (via fetch para recarregar rápido) ======
(() => {
  async function hook(selector){
    document.querySelectorAll(selector).forEach(form=>{
      form.addEventListener("submit", async e=>{
        e.preventDefault();
        const btn = form.querySelector("button");
        if (btn){ btn.disabled = true; btn.textContent = "Desligando..."; }
        try {
          await fetch(form.action, { method: form.method || "POST" });
        } finally {
          location.reload();
        }
      });
    });
  }
  hook("form.form-desligar");
  hook("form.form-desligar-todos");
})();

// ====== ROBÔ DE SESSÃO ======
(() => {
  const form = document.getElementById("formSessionBot");
  if (!form) return;
  const logEl = document.getElementById("sessionBotLog");
  const btnPause = document.getElementById("btnPause");
  const btnStop = document.getElementById("btnStop");
  const btnStatus = document.getElementById("btnStatus");
  let currentPorta = null;
  let paused = false;

  const append = m => { logEl.textContent += m + "\n"; logEl.scrollTop = logEl.scrollHeight; };

  async function post(url, payload){
    const res = await fetch(url, {
      method:"POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  form.addEventListener("submit", async e=>{
    e.preventDefault();
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    
    // Adiciona notificação WhatsApp se selecionada
    payload.notify_whatsapp = document.getElementById("chkNotifyWpp")?.checked || false;
    
    currentPorta = payload.porta;
    try {
      const r = await post("/bots/start", payload);
      paused = false;
      append(`✅ ROBÔ INICIADO na porta ${payload.porta}`);
      append(`🔍 Procurando por: "${payload.texto_alvo}"`);
      append(`📱 WhatsApp: ${payload.notify_whatsapp ? 'ATIVO' : 'inativo'}`);
      append(`⏱️ Intervalo: ${payload.intervalo}s`);
      append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
      append(JSON.stringify(r, null, 2));
    } catch(err) {
      append("❌ ERRO AO INICIAR: " + err.message);
    }
  });

  btnPause.addEventListener("click", async ()=>{
    if (!currentPorta) return append("⚠️ Defina porta primeiro.");
    try {
      const r = await post("/bots/pause", { porta: currentPorta, pause: !paused });
      paused = r.paused;
      append("⏸️ " + (paused? "PAUSADO":"RETOMADO"));
    } catch(err) {
      append("❌ ERRO PAUSE: " + err.message);
    }
  });

  btnStop.addEventListener("click", async ()=>{
    if (!currentPorta) return append("⚠️ Defina porta primeiro.");
    try {
      const r = await post("/bots/stop", { porta: currentPorta });
      append("⏹️ ROBÔ PARADO");
      append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    } catch(err) {
      append("❌ ERRO STOP: " + err.message);
    }
  });

  btnStatus.addEventListener("click", async ()=>{
    try {
      const data = await fetch("/bots/status").then(r=>r.json());
      append("📊 STATUS:");
      for (const [serial, status] of Object.entries(data)) {
        append(`📱 ${serial}:`);
        append(`  🔄 Rodando: ${status.running ? '✅' : '❌'}`);
        append(`  ⏸️ Pausado: ${status.paused ? '✅' : '❌'}`);
        append(`  🔢 Ciclos: ${status.cycles}`);
        append(`  📄 Resultado: ${status.last_result || 'nenhum'}`);
        append(`  🔍 Procurando: "${status.texto_alvo}"`);
        append("  ────────────────────────");
      }
    } catch(err) {
      append("❌ ERRO STATUS: " + err.message);
    }
  });
})();