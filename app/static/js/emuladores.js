// filepath: c:\Users\Dev\robo\robo\app\static\js\emuladores.js
(() => {
  // Se você tiver um formulário de duplicação, mantenha este bloco; senão, ele apenas não roda.
  const form = document.getElementById("formDuplicar");
  if (!form) return;

  const btn = document.getElementById("btnDuplicar");
  const spinner = document.getElementById("spinnerDuplicar");
  const label = document.getElementById("labelBtnDuplicar");
  const alerta = document.getElementById("alertaDuplicacao");

  const modalEl = document.getElementById("modalDuplicacao");
  const modal = modalEl ? new bootstrap.Modal(modalEl) : null;
  const statusEl = document.getElementById("statusDuplicacao");
  const resultadoEl = document.getElementById("resultadoDuplicacao");

  function setLoading(isLoading) {
    if (!spinner || !btn || !label) return;
    spinner.classList.toggle("d-none", !isLoading);
    btn.disabled = isLoading;
    label.textContent = isLoading ? "Aguarde..." : "Duplicar";
  }

  function alertHtml(kind, msg) {
    return `<div class="alert alert-${kind} alert-dismissible fade show" role="alert">
      ${msg}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
    </div>`;
  }

  async function postDuplicar(data) {
    const res = await fetch("/duplicar_avd", { method: "POST", body: data });
    return res.json();
  }

  async function pollStatus(taskId) {
    const res = await fetch(`/status/${taskId}`);
    return res.json();
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!modal) return;
    if (alerta) alerta.innerHTML = "";
    if (resultadoEl) resultadoEl.classList.add("d-none");
    if (statusEl) statusEl.textContent = "Iniciando clonagem...";

    setLoading(true);
    modal.show();

    try {
      const json = await postDuplicar(new FormData(form));
      if (json.erro) {
        if (alerta) alerta.innerHTML = alertHtml("danger", json.erro);
        setLoading(false);
        return;
      }
      const { task_id } = json;

      const interval = setInterval(async () => {
        try {
          const { status, erro } = await pollStatus(task_id);
          if (erro || status === "concluido") {
            clearInterval(interval);
            setLoading(false);
            if (resultadoEl) resultadoEl.classList.remove("d-none");
            if (erro) {
              if (resultadoEl) resultadoEl.innerHTML = alertHtml("danger", erro);
            } else {
              if (resultadoEl) resultadoEl.innerHTML = alertHtml("success", "AVD duplicado com sucesso!");
              setTimeout(() => window.location.reload(), 1200);
            }
          } else if (statusEl) {
            statusEl.textContent = `Progresso: ${status || "em andamento"}...`;
          }
        } catch {
          clearInterval(interval);
          setLoading(false);
          if (resultadoEl) {
            resultadoEl.classList.remove("d-none");
            resultadoEl.innerHTML = alertHtml("danger", "Falha ao consultar status da tarefa.");
          }
        }
      }, 1000);
    } catch {
      if (alerta) alerta.innerHTML = alertHtml("danger", "Erro ao iniciar a duplicação.");
      setLoading(false);
    }
  });
})();

(() => {
  const banner = document.getElementById("startBusyBanner");
  const getButtons = () => [
    ...document.querySelectorAll(".btn-ligar"),
    ...document.querySelectorAll(".btn-ligar-all"),
  ];

  function setButtonsBusy(busy) {
    getButtons().forEach((btn) => {
      btn.disabled = busy;
      const sp = btn.querySelector(".spinner-border");
      if (sp) sp.classList.toggle("d-none", !busy);
    });
    if (banner) banner.classList.toggle("d-none", !busy);
  }

  let prevBusy = false;
  async function pollBusy() {
    try {
      const res = await fetch("/status/start_busy", { cache: "no-store" });
      const { busy } = await res.json();
      setButtonsBusy(Boolean(busy));
      if (prevBusy && !busy) window.location.reload();
      prevBusy = Boolean(busy);
    } catch {}
  }

  // Desabilita imediatamente ao enviar qualquer form de ligar (individual ou todos)
  document.querySelectorAll("form").forEach((f) => {
    const btn = f.querySelector(".btn-ligar, .btn-ligar-all");
    if (btn) f.addEventListener("submit", () => setButtonsBusy(true));
  });

  pollBusy();
  setInterval(pollBusy, 1500);
})();

(() => {
  // Recarrega a tela após concluir POST de desligar (individual e todos)
  async function hookPostAndReload(selector) {
    document.querySelectorAll(selector).forEach((form) => {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = form.querySelector("button");
        if (btn) {
          btn.disabled = true;
          btn.dataset._oldText = btn.textContent || "";
          btn.textContent = "Desligando...";
        }
        try {
          const res = await fetch(form.action, {
            method: form.method || "POST",
            body: new FormData(form),
          });
          // Independentemente do redirect, atualize a lista
          if (res.ok) window.location.reload();
          else window.location.reload();
        } catch {
          window.location.reload();
        }
      });
    });
  }

  hookPostAndReload('form[action^="/parar/"]');
  hookPostAndReload('form[action="/desligar_todos"]');
})();