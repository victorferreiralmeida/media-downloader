const API_BASE = window.API_BASE;

const urlInput = document.getElementById("url-input");
const pasteBtn = document.getElementById("paste-btn");
const downloadBtn = document.getElementById("download-btn");
const formatNamesCheckbox = document.getElementById("format-names");
const fmtMp4Btn = document.getElementById("fmt-mp4");
const fmtMp3Btn = document.getElementById("fmt-mp3");
const progressSection = document.getElementById("progress-section");
const progressMessage = document.getElementById("progress-message");
const progressFill = document.getElementById("progress-fill");
const statusMessage = document.getElementById("status-message");
const previewCard = document.getElementById("preview-card");
const videoTitle = document.getElementById("video-title");
const videoMeta = document.getElementById("video-meta");
const videoDescription = document.getElementById("video-description");
const thumbnail = document.getElementById("thumbnail");
const thumbnailPlaceholder = document.getElementById("thumbnail-placeholder");
const aboutBtn = document.getElementById("about-btn");
const servicesBtn = document.getElementById("services-btn");
const aboutDialog = document.getElementById("about-dialog");
const servicesDialog = document.getElementById("services-dialog");
const ethicsLink = document.getElementById("ethics-link");

let currentInfo = null;
let activeEventSource = null;
let isDownloading = false;
let selectedFormat = "mp4";
let fetchDebounce = null;

function isValidMediaUrl(text) {
  try {
    const parsed = new URL(text.trim());
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function setStatus(text, type = "") {
  statusMessage.textContent = text;
  statusMessage.className = `status ${type ? `status--${type}` : ""}`.trim();
}

function setDownloadReady(ready) {
  downloadBtn.disabled = !ready || isDownloading;
  downloadBtn.classList.toggle("icon-btn--ready", ready && !isDownloading);
}

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function showThumbnail(url) {
  if (url) {
    thumbnail.src = url;
    thumbnail.alt = videoTitle.textContent;
    thumbnail.classList.remove("hidden");
    thumbnailPlaceholder.classList.add("hidden");
  } else {
    thumbnail.classList.add("hidden");
    thumbnail.removeAttribute("src");
    thumbnailPlaceholder.classList.remove("hidden");
  }
}

function showPreview(show) {
  previewCard.classList.toggle("hidden", !show);
}

function showProgress(show) {
  progressSection.classList.toggle("hidden", !show);
  if (!show) {
    progressFill.style.width = "0%";
    progressMessage.textContent = "";
  }
}

function updateProgress(progress, message) {
  const pct = Math.min(100, Math.max(0, Math.round(progress * 100)));
  progressFill.style.width = `${pct}%`;
  progressMessage.textContent = (message || "processando...").toLowerCase();
}

function selectFormat(format) {
  selectedFormat = format;
  fmtMp4Btn.classList.toggle("format-btn--active", format === "mp4");
  fmtMp3Btn.classList.toggle("format-btn--active", format === "mp3");
}

function resetPreview() {
  currentInfo = null;
  setDownloadReady(false);
  showPreview(false);
  videoTitle.textContent = "—";
  videoMeta.innerHTML = "";
  videoDescription.textContent = "";
  showThumbnail("");
}

async function apiPost(path, body) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    const hint =
      window.location.port === "8000"
        ? "Verifique se a API está rodando."
        : "Abra http://127.0.0.1:8000 ou verifique se a API está rodando.";
    throw new Error(`Não foi possível conectar à API. ${hint}`);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg).join(", ")
      : detail || `Erro ${response.status}`;
    throw new Error(msg);
  }
  return data;
}

function renderPreview(info) {
  videoTitle.textContent = info.title;

  const metaParts = [
    `<span>${formatDuration(info.duration)}</span>`,
    `<span>${info.channel}</span>`,
  ];
  if (info.is_playlist) {
    metaParts.push(`<span>${info.entry_count} vídeos</span>`);
  }
  videoMeta.innerHTML = metaParts.join("");
  videoDescription.textContent = info.description
    ? info.description.slice(0, 120) + (info.description.length > 120 ? "…" : "")
    : "";

  showThumbnail(info.thumbnail);
  showPreview(true);
}

async function fetchInfo() {
  const url = urlInput.value.trim();
  if (!url) {
    setStatus("cole um link primeiro", "error");
    return;
  }

  if (!isValidMediaUrl(url)) {
    resetPreview();
    setStatus("informe um link válido (http:// ou https://)", "error");
    return;
  }

  setStatus("buscando link...", "loading");
  setDownloadReady(false);

  try {
    currentInfo = await apiPost("/api/info", { url });
    renderPreview(currentInfo);
    setDownloadReady(true);
    setStatus("");
  } catch (error) {
    resetPreview();
    setStatus(error.message, "error");
  }
}

function scheduleFetch() {
  clearTimeout(fetchDebounce);
  const url = urlInput.value.trim();
  if (!url) {
    resetPreview();
    setStatus("");
    return;
  }
  if (!isValidMediaUrl(url)) {
    resetPreview();
    setStatus("");
    return;
  }
  fetchDebounce = setTimeout(fetchInfo, 600);
}

function closeEventSource() {
  if (activeEventSource) {
    activeEventSource.close();
    activeEventSource = null;
  }
}

function parseContentDisposition(header) {
  if (!header) return null;

  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  const match = header.match(/filename="?([^";]+)"?/i);
  return match ? match[1] : null;
}

function watchProgress(jobId) {
  return new Promise((resolve, reject) => {
    let finished = false;

    activeEventSource = new EventSource(`${API_BASE}/api/progress/${jobId}`);

    activeEventSource.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      updateProgress(data.progress ?? 0, data.message ?? "");

      if (data.status === "completed") {
        finished = true;
        closeEventSource();
        resolve(data);
      } else if (data.status === "failed") {
        finished = true;
        closeEventSource();
        reject(new Error(data.error || data.message || "falha no download"));
      }
    };

    activeEventSource.onerror = () => {
      closeEventSource();
      if (!finished) {
        reject(new Error("conexão com o servidor perdida"));
      }
    };
  });
}

async function triggerBrowserDownload(jobId, filename) {
  const response = await fetch(`${API_BASE}/api/file/${jobId}`);
  if (!response.ok) throw new Error("não foi possível obter o arquivo");

  const serverFilename = parseContentDisposition(response.headers.get("Content-Disposition"));
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename || serverFilename || "download";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);

  fetch(`${API_BASE}/api/job/${jobId}`, { method: "DELETE" }).catch(() => {});
}

async function startDownload() {
  const url = urlInput.value.trim();
  if (!url) {
    setStatus("cole um link primeiro", "error");
    return;
  }

  if (!currentInfo) await fetchInfo();
  if (!currentInfo) return;

  isDownloading = true;
  setDownloadReady(false);
  showProgress(true);
  updateProgress(0, "iniciando...");
  setStatus("");

  try {
    const { job_id } = await apiPost("/api/download", {
      url,
      format: selectedFormat,
      format_names: formatNamesCheckbox.checked,
    });

    const result = await watchProgress(job_id);
    updateProgress(1, "enviando ao navegador...");
    await triggerBrowserDownload(job_id, result.filename);
    setStatus("pronto — salvo nos seus downloads", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    isDownloading = false;
    showProgress(false);
    setDownloadReady(!!currentInfo);
    closeEventSource();
  }
}

async function pasteFromClipboard() {
  try {
    const text = await navigator.clipboard.readText();
    const trimmed = text.trim();
    if (!trimmed) return;
    urlInput.value = trimmed;
    urlInput.focus();
    if (!isValidMediaUrl(trimmed)) {
      resetPreview();
      setStatus("informe um link válido (http:// ou https://)", "error");
      return;
    }
    scheduleFetch();
  } catch {
    setStatus("não foi possível ler a área de transferência", "error");
  }
}

function openDialog(dialog) {
  if (typeof dialog.showModal === "function") dialog.showModal();
}

function closeDialog(dialog) {
  if (typeof dialog.close === "function") dialog.close();
}

document.querySelectorAll(".dialog__close").forEach((btn) => {
  btn.addEventListener("click", () => {
    closeDialog(btn.closest("dialog"));
  });
});

aboutBtn.addEventListener("click", () => openDialog(aboutDialog));
servicesBtn.addEventListener("click", () => openDialog(servicesDialog));
ethicsLink.addEventListener("click", (e) => {
  e.preventDefault();
  openDialog(aboutDialog);
});

pasteBtn.addEventListener("click", pasteFromClipboard);
downloadBtn.addEventListener("click", startDownload);

fmtMp4Btn.addEventListener("click", () => selectFormat("mp4"));
fmtMp3Btn.addEventListener("click", () => selectFormat("mp3"));

urlInput.addEventListener("input", scheduleFetch);

urlInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    clearTimeout(fetchDebounce);
    fetchInfo();
  }
});

urlInput.addEventListener("paste", () => {
  setTimeout(scheduleFetch, 50);
});
