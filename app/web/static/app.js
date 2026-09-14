"use strict";

const state = { projectName: "", project: null, script: null, scene: 0, jobTimer: null };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const titles = { projects: "Projects", script: "Script editor", assets: "Asset library", voice: "Voice lab", render: "Render desk" };

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const type = response.headers.get("content-type") || "";
  const body = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(body.detail || body || `Request failed (${response.status})`);
  return body;
}

function toast(message, bad = false) {
  const node = $("#toast");
  node.textContent = message;
  node.style.borderColor = bad ? "#ff7f8e88" : "#63d6a477";
  node.classList.add("show");
  window.clearTimeout(node._timer);
  node._timer = window.setTimeout(() => node.classList.remove("show"), 2800);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function showView(name) {
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  $("#page-title").textContent = titles[name];
  history.replaceState(null, "", `#${name}`);
  if (name === "assets") loadAssets();
}

async function loadProjects(selectName = state.projectName) {
  const projects = await api("/api/projects");
  const select = $("#project-select");
  select.innerHTML = '<option value="">Choose a project</option>' + projects.map((project) => `<option value="${escapeHtml(project.name)}">${escapeHtml(project.title)}</option>`).join("");
  select.value = selectName;
  $("#project-grid").innerHTML = projects.map((project) => `<article class="project-card" data-project="${escapeHtml(project.name)}"><div class="thumb">✦</div><h3>${escapeHtml(project.title)}</h3><p>${project.invalid ? "Configuration needs attention" : "Open project workspace"}</p></article>`).join("");
  $("#project-empty").hidden = projects.length > 0;
}

async function openProject(name, destination = "script") {
  if (!name) return;
  try {
    const data = await api(`/api/projects/${encodeURIComponent(name)}`);
    state.projectName = name;
    state.project = data.project;
    state.script = data.script;
    state.scene = 0;
    $("#project-select").value = name;
    renderScript();
    resetRender();
    showView(destination);
    toast(`Opened ${data.project.name}`);
  } catch (error) { toast(error.message, true); }
}

async function createProject(event) {
  event.preventDefault();
  const name = $("#project-name").value.trim();
  if (!name) return;
  const button = $("#create-project");
  button.disabled = true;
  try {
    const result = await api("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });
    $("#project-dialog").close();
    $("#project-form").reset();
    await loadProjects(result.name);
    await openProject(result.name);
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

function currentScene() { return state.script?.scenes?.[state.scene]; }

function renderScript() {
  const ready = Boolean(state.project && state.script);
  $("#script-notice").textContent = ready ? `${state.project.name} · ${state.script.scenes.length} scene${state.script.scenes.length === 1 ? "" : "s"}` : "Choose a project to start writing.";
  $("#scene-tabs").innerHTML = ready ? state.script.scenes.map((scene, index) => `<button class="${index === state.scene ? "active" : ""}" data-scene="${index}">${escapeHtml(scene.scene_id)}</button>`).join("") : "";
  const scene = currentScene();
  $("#block-list").innerHTML = scene ? scene.events.map(blockTemplate).join("") : "";
  $("#add-row").hidden = !scene;
  $("#save-script").disabled = !scene;
}

function blockTemplate(event, index) {
  const type = event.type;
  const speakers = state.project.characters || [];
  let fields;
  if (type === "dialogue") {
    fields = `<label>Speaker<select data-field="speaker">${speakers.map((character) => `<option ${character.name === event.speaker ? "selected" : ""}>${escapeHtml(character.name)}</option>`).join("")}</select></label><label>Dialogue<input data-field="text" value="${escapeHtml(event.text)}"></label><label>Duration<input value="Auto from voice" disabled></label><label class="full">Caption<input data-field="caption" value="${escapeHtml(event.caption || "")}" placeholder="Defaults to dialogue text"></label>`;
  } else {
    const textKey = type === "caption" ? "text" : "description";
    fields = `<label class="full">${type === "caption" ? "Caption" : "Action"}<input data-field="${textKey}" value="${escapeHtml(event[textKey] || "")}" placeholder="Describe this ${type}"></label><label>Duration (seconds)<input data-field="duration_seconds" type="number" min="0.1" step="0.1" value="${escapeHtml(event.duration_seconds || 1)}"></label>`;
  }
  return `<article class="script-block" data-index="${index}"><span class="drag">⠿</span><span class="type-pill">${escapeHtml(type)}</span><div class="block-fields">${fields}</div><div class="block-actions"><button data-move="up" title="Move up">↑</button><button data-move="down" title="Move down">↓</button><button data-delete title="Delete">×</button></div></article>`;
}

function editBlock(event) {
  const block = event.target.closest(".script-block");
  if (!block) return;
  const item = currentScene().events[Number(block.dataset.index)];
  const field = event.target.dataset.field;
  if (field) item[field] = field === "duration_seconds" ? Number(event.target.value) : event.target.value;
}

function actOnBlock(event) {
  const block = event.target.closest(".script-block");
  if (!block) return;
  const events = currentScene().events;
  const index = Number(block.dataset.index);
  if (event.target.dataset.delete !== undefined) events.splice(index, 1);
  if (event.target.dataset.move === "up" && index > 0) [events[index - 1], events[index]] = [events[index], events[index - 1]];
  if (event.target.dataset.move === "down" && index < events.length - 1) [events[index + 1], events[index]] = [events[index], events[index + 1]];
  renderScript();
}

function addBlock(type) {
  const scene = currentScene();
  if (!scene) return toast("Open a project first", true);
  if (type === "dialogue") scene.events.push({ type, speaker: state.project.characters?.[0]?.name || "Narrator", text: "New dialogue", caption: "" });
  if (type === "action") scene.events.push({ type, description: "Describe the action", duration_seconds: 1 });
  if (type === "caption") scene.events.push({ type, text: "On-screen caption", duration_seconds: 2 });
  renderScript();
}

async function saveScript() {
  if (!state.projectName) return toast("Open a project first", true);
  try {
    await api(`/api/projects/${encodeURIComponent(state.projectName)}/script`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: state.script }) });
    toast("Script saved");
  } catch (error) { toast(error.message, true); }
}

async function loadAssets() {
  try {
    const assets = await api("/api/assets");
    $("#asset-grid").innerHTML = assets.map((asset) => `<article class="asset-card"><div class="asset-icon">◇</div><h3>${escapeHtml(asset.path.split("/").pop())}</h3><p>${escapeHtml(asset.path)} · ${(asset.size / 1024).toFixed(1)} KB</p></article>`).join("") || '<div class="notice">No assets imported yet.</div>';
  } catch (error) { toast(error.message, true); }
}

async function importAsset() {
  const file = $("#asset-file").files[0];
  if (!file) return toast("Choose a file to import", true);
  const category = $("#asset-category").value;
  const button = $("#import-asset");
  button.disabled = true;
  try {
    await api(`/api/assets/${category}?filename=${encodeURIComponent(file.name)}`, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file });
    $("#asset-file").value = "";
    toast(`Imported ${file.name}`);
    await loadAssets();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function previewVoice() {
  const status = $("#voice-status");
  status.textContent = "Generating local audio…";
  $("#preview-voice").disabled = true;
  try {
    const result = await api("/api/voice-preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ voice: $("#voice-id").value, text: $("#voice-text").value }) });
    const player = $("#voice-player");
    player.src = `${result.url}?t=${Date.now()}`;
    player.load();
    status.textContent = "Preview ready";
    const download = $("#voice-download");
    download.href = result.url; download.hidden = false;
    await player.play().catch(() => {});
  } catch (error) { status.textContent = "Preview failed"; toast(error.message, true); }
  finally { $("#preview-voice").disabled = false; }
}

function resetRender() {
  $("#validation-result").className = "status-line muted";
  $("#validation-result").innerHTML = "<i></i>Not checked yet";
  $("#render-stage").textContent = "Waiting for a render";
  $("#render-percent").textContent = "0%";
  $("#render-progress").style.width = "0%";
  $("#render-outputs").innerHTML = "";
}

async function validateProject() {
  if (!state.projectName) return toast("Open a project first", true);
  const result = $("#validation-result");
  result.className = "status-line muted"; result.innerHTML = "<i></i>Checking project…";
  try {
    const data = await api(`/api/projects/${encodeURIComponent(state.projectName)}/validate`, { method: "POST" });
    result.className = "status-line good"; result.innerHTML = `<i></i>Ready · ${data.assets} assets · ${data.scenes} scenes`;
    return true;
  } catch (error) {
    result.className = "status-line bad"; result.innerHTML = `<i></i>${escapeHtml(error.message)}`;
    return false;
  }
}

async function startRender(dryRun) {
  if (!state.projectName) return toast("Open a project first", true);
  if (!(await validateProject())) return;
  try {
    const data = await api(`/api/projects/${encodeURIComponent(state.projectName)}/render?dry_run=${dryRun}`, { method: "POST" });
    $("#render-error").hidden = true; $("#render-outputs").innerHTML = "";
    window.clearInterval(state.jobTimer);
    await pollRender(data.job_id);
    state.jobTimer = window.setInterval(() => pollRender(data.job_id), 700);
  } catch (error) { toast(error.message, true); }
}

async function pollRender(jobId) {
  try {
    const job = await api(`/api/renders/${jobId}`);
    $("#render-stage").textContent = job.stage.replace(/^./, (letter) => letter.toUpperCase());
    $("#render-percent").textContent = `${job.progress}%`;
    $("#render-progress").style.width = `${job.progress}%`;
    $("#render-message").textContent = job.status === "complete" ? `${job.kind === "dry-run" ? "Dry-run" : "Render"} completed successfully.` : `Pipeline is ${job.stage}…`;
    if (job.status === "failed") {
      window.clearInterval(state.jobTimer);
      $("#render-error").textContent = job.error; $("#render-error").hidden = false;
    }
    if (job.status === "complete") {
      window.clearInterval(state.jobTimer);
      renderOutputs(job.artifacts);
      toast(job.kind === "dry-run" ? "Dry-run complete" : "Video render complete");
    }
  } catch (error) { window.clearInterval(state.jobTimer); toast(error.message, true); }
}

function renderOutputs(artifacts) {
  $("#render-outputs").innerHTML = artifacts.map((artifact) => {
    const preview = artifact.kind === "mp4" ? `<video src="${artifact.url}" controls preload="metadata"></video>` : artifact.kind === "wav" ? `<audio src="${artifact.url}" controls preload="metadata"></audio>` : "";
    return `<article class="output-card"><p class="eyebrow">${escapeHtml(artifact.kind.toUpperCase())}</p><h3>${escapeHtml(artifact.name)}</h3>${preview}<a href="${artifact.url}" download>Open / download ↗</a></article>`;
  }).join("") || '<div class="notice">The job completed without downloadable media.</div>';
}

document.addEventListener("DOMContentLoaded", async () => {
  $$(".nav-item").forEach((item) => item.addEventListener("click", () => showView(item.dataset.view)));
  $("#new-project").addEventListener("click", () => $("#project-dialog").showModal());
  $("#project-form").addEventListener("submit", createProject);
  $("#refresh-projects").addEventListener("click", () => loadProjects().catch((error) => toast(error.message, true)));
  $("#project-grid").addEventListener("click", (event) => { const card = event.target.closest("[data-project]"); if (card) openProject(card.dataset.project); });
  $("#project-select").addEventListener("change", (event) => openProject(event.target.value));
  $("#scene-tabs").addEventListener("click", (event) => { if (event.target.dataset.scene !== undefined) { state.scene = Number(event.target.dataset.scene); renderScript(); } });
  $("#block-list").addEventListener("input", editBlock); $("#block-list").addEventListener("click", actOnBlock);
  $("#add-row").addEventListener("click", (event) => { if (event.target.dataset.add) addBlock(event.target.dataset.add); });
  $("#save-script").addEventListener("click", saveScript);
  $("#import-asset").addEventListener("click", importAsset);
  $("#asset-file").addEventListener("change", (event) => { const file = event.target.files[0]; if (file) $(".file-drop strong").textContent = file.name; });
  $("#preview-voice").addEventListener("click", previewVoice);
  $("#validate-project").addEventListener("click", validateProject);
  $("#dry-run").addEventListener("click", () => startRender(true));
  $("#start-render").addEventListener("click", () => startRender(false));
  showView(location.hash.slice(1) in titles ? location.hash.slice(1) : "projects");
  try { await loadProjects(); } catch (error) { toast(error.message, true); }
});
