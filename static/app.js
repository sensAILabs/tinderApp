(() => {
  const STORAGE_KEY = "vehicle_tinder_annotator";

  const startScreen = document.getElementById("start-screen");
  const appScreen = document.getElementById("app-screen");
  const annotatorInput = document.getElementById("annotator-input");
  const startBtn = document.getElementById("start-btn");
  const startStatus = document.getElementById("start-status");
  const annotatorLabel = document.getElementById("annotator-label");
  const progressText = document.getElementById("progress-text");
  const progressCounts = document.getElementById("progress-counts");
  const progressFill = document.getElementById("progress-fill");
  const card = document.getElementById("card");
  const cardImage = document.getElementById("card-image");
  const cardName = document.getElementById("card-name");
  const cardSource = document.getElementById("card-source");
  const emptyState = document.getElementById("empty-state");
  const stampEv = card.querySelector(".stamp-ev");
  const stampIce = card.querySelector(".stamp-ice");

  let annotator = localStorage.getItem(STORAGE_KEY) || "";
  let current = null;
  let busy = false;
  let drag = null;

  const THRESHOLD = 110;

  annotatorInput.value = annotator;

  async function api(path, options) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || `Request failed (${res.status})`);
    }
    return data;
  }

  function updateProgress(progress) {
    if (!progress) return;
    const { total, labeled, by_label: byLabel } = progress;
    const pct = total ? Math.round((labeled / total) * 100) : 0;
    progressText.textContent = `${labeled} / ${total} (${pct}%)`;
    progressCounts.textContent = `EV ${byLabel?.ev || 0} · ICE ${byLabel?.ice || 0} · skip ${byLabel?.skip || 0}`;
    progressFill.style.width = `${pct}%`;
  }

  function showDone() {
    current = null;
    card.classList.add("hidden");
    emptyState.classList.remove("hidden");
  }

  function showImage(image) {
    if (!image) {
      showDone();
      return;
    }
    current = image;
    emptyState.classList.add("hidden");
    card.classList.remove("hidden");
    card.style.transition = "none";
    card.style.transform = "";
    card.style.opacity = "1";
    stampEv.style.opacity = "0";
    stampIce.style.opacity = "0";
    cardImage.src = image.url;
    cardName.textContent = image.filename;
    cardSource.textContent = image.source_folder
      ? `from /${image.source_folder}`
      : "";
    // Force reflow then restore transition for swipes.
    void card.offsetWidth;
    card.style.transition = "";
  }

  async function loadNext(afterId) {
    const qs = afterId ? `?after=${encodeURIComponent(afterId)}` : "";
    const data = await api(`/api/next${qs}`);
    updateProgress(data.progress);
    showImage(data.image);
  }

  async function submitLabel(label) {
    if (!current || busy) return;
    busy = true;
    const imageId = current.image_id;
    try {
      await flyOff(label);
      const data = await api("/api/label", {
        method: "POST",
        body: JSON.stringify({
          image_id: imageId,
          label,
          annotator,
        }),
      });
      updateProgress(data.progress);
      showImage(data.next);
    } catch (err) {
      startStatus.textContent = err.message;
      card.style.transform = "";
      card.style.opacity = "1";
      stampEv.style.opacity = "0";
      stampIce.style.opacity = "0";
    } finally {
      busy = false;
    }
  }

  function flyOff(label) {
    return new Promise((resolve) => {
      const x = label === "ev" ? window.innerWidth : label === "ice" ? -window.innerWidth : 0;
      const y = label === "skip" ? -window.innerHeight * 0.4 : 0;
      const rot = label === "ev" ? 24 : label === "ice" ? -24 : 0;
      card.style.transition = "transform 0.28s ease, opacity 0.28s ease";
      card.style.transform = `translate(${x}px, ${y}px) rotate(${rot}deg)`;
      card.style.opacity = "0";
      if (label === "ev") stampEv.style.opacity = "1";
      if (label === "ice") stampIce.style.opacity = "1";
      setTimeout(resolve, 260);
    });
  }

  async function undo() {
    if (busy) return;
    busy = true;
    try {
      const data = await api("/api/undo", { method: "POST", body: "{}" });
      updateProgress(data.progress);
      showImage(data.image);
    } catch (err) {
      console.warn(err.message);
    } finally {
      busy = false;
    }
  }

  function onPointerDown(event) {
    if (!current || busy) return;
    drag = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
    };
    card.setPointerCapture(event.pointerId);
    card.style.transition = "none";
  }

  function onPointerMove(event) {
    if (!drag || event.pointerId !== drag.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    const rot = dx / 18;
    card.style.transform = `translate(${dx}px, ${dy}px) rotate(${rot}deg)`;
    const evOpacity = Math.min(1, Math.max(0, dx / THRESHOLD));
    const iceOpacity = Math.min(1, Math.max(0, -dx / THRESHOLD));
    stampEv.style.opacity = String(evOpacity);
    stampIce.style.opacity = String(iceOpacity);
  }

  function onPointerUp(event) {
    if (!drag || event.pointerId !== drag.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    drag = null;
    card.style.transition = "";

    if (dx > THRESHOLD) {
      submitLabel("ev");
      return;
    }
    if (dx < -THRESHOLD) {
      submitLabel("ice");
      return;
    }
    if (dy < -THRESHOLD * 1.2) {
      submitLabel("skip");
      return;
    }

    card.style.transform = "";
    stampEv.style.opacity = "0";
    stampIce.style.opacity = "0";
  }

  function bindControls() {
    document.getElementById("btn-ev").addEventListener("click", () => submitLabel("ev"));
    document.getElementById("btn-ice").addEventListener("click", () => submitLabel("ice"));
    document.getElementById("btn-skip").addEventListener("click", () => submitLabel("skip"));
    document.getElementById("btn-undo").addEventListener("click", undo);

    card.addEventListener("pointerdown", onPointerDown);
    card.addEventListener("pointermove", onPointerMove);
    card.addEventListener("pointerup", onPointerUp);
    card.addEventListener("pointercancel", onPointerUp);

    window.addEventListener("keydown", (event) => {
      if (appScreen.classList.contains("hidden")) return;
      if (event.target && ["INPUT", "TEXTAREA"].includes(event.target.tagName)) return;
      if (event.key === "ArrowRight") submitLabel("ev");
      else if (event.key === "ArrowLeft") submitLabel("ice");
      else if (event.key === "ArrowUp") submitLabel("skip");
      else if (event.key === "z" || event.key === "Z") undo();
    });
  }

  startBtn.addEventListener("click", async () => {
    if (location.protocol === "file:") {
      startStatus.textContent =
        "Open the app with “Start Vehicle Tinder”, not by opening this HTML file.";
      return;
    }
    annotator = annotatorInput.value.trim() || "anonymous";
    localStorage.setItem(STORAGE_KEY, annotator);
    annotatorLabel.textContent = `Annotator: ${annotator}`;
    startBtn.disabled = true;
    startStatus.textContent = "Loading images…";
    try {
      const cfg = await api("/api/config");
      updateProgress(cfg.progress);
      if (!cfg.dataset_root || (cfg.progress && cfg.progress.total === 0)) {
        startStatus.textContent =
          "No images found. Put photos in images/ev and images/ice, then click Start again.";
        startBtn.disabled = false;
        return;
      }
      startScreen.classList.add("hidden");
      appScreen.classList.remove("hidden");
      await loadNext();
    } catch (err) {
      startStatus.textContent =
        `${err.message}. Make sure you launched “Start Vehicle Tinder” and kept that window open.`;
      startBtn.disabled = false;
    }
  });

  bindControls();
})();
