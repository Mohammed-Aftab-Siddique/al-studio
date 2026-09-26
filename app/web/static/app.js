"use strict";

const state = { projectName: "", project: null, script: null, scene: 0, composerScene: 0, selectedInstance: "", composerAssets: [], pointerDrag: null, animationPreviewTime: null, animationPreviewFrame: null, jobTimer: null, creativeKind: "" };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const titles = { projects: "Projects", scene: "Scene composer", script: "Script editor", creative: "Creative lab", assets: "Asset library", voice: "Voice lab", render: "Render desk" };

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
  if (name === "scene") { loadComposerAssets(); renderComposer(); }
  if (name === "creative") loadCreativeDrafts();
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
    if (state.animationPreviewFrame !== null) cancelAnimationFrame(state.animationPreviewFrame);
    state.animationPreviewFrame = null;
    state.animationPreviewTime = null;
    const data = await api(`/api/projects/${encodeURIComponent(name)}`);
    state.projectName = name;
    state.project = data.project;
    state.script = data.script;
    state.scene = 0;
    state.composerScene = 0;
    state.selectedInstance = "";
    state.creativeKind = "";
    $("#creative-result").value = "";
    $("#creative-result-title").textContent = "No draft yet";
    $("#creative-dirty-state").textContent = "Not saved";
    $("#save-creative").disabled = true;
    $("#apply-creative").disabled = true;
    $("#project-select").value = name;
    renderScript();
    renderComposer();
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

function assetUrl(path) {
  return `/asset-media/${path.split("/").map(encodeURIComponent).join("/")}`;
}

function currentProjectScene() {
  return state.project?.scenes?.[state.composerScene];
}

function scriptSceneFor(projectScene) {
  return state.script?.scenes?.find((scene) => scene.scene_id === projectScene?.id);
}

function uniqueId(base, existing) {
  const clean = base.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "asset";
  let candidate = clean;
  let number = 2;
  while (existing.has(candidate)) candidate = `${clean}-${number++}`;
  return candidate;
}

function normalizeSceneInstances(scene) {
  if (!scene) return;
  scene.instances ||= [];
  scene.animations ||= [];
  const ids = new Set(scene.instances.map((item) => item.id));
  const placedAssets = new Set(scene.instances.map((item) => item.asset_id));
  (scene.prop_asset_ids || []).forEach((assetId, index) => {
    if (placedAssets.has(assetId)) return;
    const id = uniqueId(assetId, ids);
    ids.add(id);
    scene.instances.push({ id, asset_id: assetId, x: 1030 + index * 55, y: 405, width: 140, height: 205, rotation: 0, opacity: 1, z_index: index, visible: true });
  });
  scene.prop_asset_ids = [];
}

function sceneTimelineData(scene) {
  const clips = { visual: [], dialogue: [], caption: [], audio: [] };
  if (!scene) return { clips, duration: 1 };
  (scene.animations || []).forEach((animation) => clips.visual.push({ start: animation.start_seconds, duration: animation.duration_seconds, label: `${animation.preset === "asset" ? animation.asset_animation_id : animation.preset === "rig" ? animation.rig_pose_id : animation.preset}${animation.loop ? " ↻" : ""}` }));
  const scriptScene = scriptSceneFor(scene);
  let cursor = 0;
  (scriptScene?.events || []).forEach((event) => {
    const duration = event.type === "dialogue" ? 2 : Number(event.duration_seconds || 1);
    const explicit = Number(event.start_seconds);
    const start = event.start_seconds === undefined || event.start_seconds === null || event.start_seconds === "" || !Number.isFinite(explicit) ? cursor : explicit;
    const label = event.type === "dialogue" ? `${event.speaker}: ${event.text}` : event.type === "caption" ? event.text : event.type === "action" ? (event.description || event.name || "Action") : (event.asset_id || event.type.replace("_", " "));
    if (event.type === "dialogue") {
      clips.dialogue.push({ start, duration, label });
      clips.audio.push({ start, duration, label: `${event.speaker} voice` });
      clips.caption.push({ start, duration, label: event.caption || event.text });
    } else if (event.type === "caption") clips.caption.push({ start, duration, label });
    else if (["ambience", "sound_effect"].includes(event.type)) clips.audio.push({ start, duration, label });
    else clips.visual.push({ start, duration, label });
    cursor = Math.max(cursor, start + duration);
  });
  const duration = Math.max(1, ...Object.values(clips).flat().map((clip) => clip.start + clip.duration));
  return { clips, duration };
}

function renderTimeline() {
  const { clips, duration } = sceneTimelineData(currentProjectScene());
  $("#timeline-duration").textContent = `≈ ${duration.toFixed(1)}s`;
  $("#timeline-ruler").innerHTML = Array.from({ length: 6 }, (_, index) => `<span class="timeline-tick" style="left:${index * 20}%">${(duration * index / 5).toFixed(1)}s</span>`).join("");
  Object.entries(clips).forEach(([track, items]) => {
    const rowEnds = [];
    const arranged = [...items].sort((a, b) => a.start - b.start).map((clip) => {
      let row = rowEnds.findIndex((end) => end <= clip.start);
      if (row < 0) row = rowEnds.length;
      rowEnds[row] = clip.start + clip.duration;
      return { ...clip, row };
    });
    const node = $(`#timeline-${track}`);
    node.style.height = `${Math.max(34, 8 + rowEnds.length * 27)}px`;
    node.innerHTML = arranged.map((clip) => {
      const left = Math.max(0, clip.start / duration * 100);
      const width = Math.max(0.8, clip.duration / duration * 100);
      return `<span class="timeline-clip ${track}" style="left:${left}%;width:${width}%;top:${4 + clip.row * 27}px" title="${escapeHtml(clip.label)} · ${clip.start.toFixed(1)}s">${escapeHtml(clip.label)}</span>`;
    }).join("");
  });
}

async function loadComposerAssets() {
  try {
    state.composerAssets = (await api("/api/assets")).filter((asset) => /\.(svg|png|webp)$/i.test(asset.path));
    renderComposerAssetTray();
  } catch (error) { toast(error.message, true); }
}

function renderComposerAssetTray() {
  const query = $("#composer-asset-search").value.trim().toLowerCase();
  const assets = state.composerAssets.filter((asset) => asset.path.toLowerCase().includes(query));
  $("#composer-asset-list").innerHTML = assets.map((asset) => {
    const name = asset.path.split("/").pop();
    const category = asset.path.split("/")[0] || "visual";
    return `<button class="composer-asset-item" draggable="true" data-asset-path="${escapeHtml(asset.path)}"><img src="${asset.url}" alt=""><span><strong>${escapeHtml(name)}</strong><small>${escapeHtml(category)}</small></span></button>`;
  }).join("") || '<div class="empty-inspector">No matching visual assets.</div>';
}

function instanceById(id) {
  return currentProjectScene()?.instances?.find((instance) => instance.id === id);
}

const animationLabels = { "fade-in": "Fade in", "fade-out": "Fade out", "slide-in": "Slide in", bounce: "Bounce", float: "Float", pulse: "Pulse", rotate: "Rotate", shake: "Shake" };

function availableAnimations(instance) {
  const asset = state.project?.assets?.find((item) => item.id === instance?.asset_id);
  const universal = asset?.kind === "scene" ? ["fade-in", "fade-out", "slide-in", "pulse"] : Object.keys(animationLabels);
  const presets = universal.map((name) => ({ value: name, label: animationLabels[name] }));
  const capabilities = (asset?.capabilities?.animations || []).map((animation) => ({ value: `asset:${animation.id}`, label: `${animation.id} · ${animation.type === "sprite_sheet" ? "Sprite sheet" : "Frame sequence"}` }));
  const poses = (asset?.capabilities?.rig?.poses || []).map((pose) => ({ value: `rig:${pose.id}`, label: `${pose.id} · Layered rig` }));
  return [...capabilities, ...poses, ...presets];
}

function animationChoice(animation) {
  if (animation.preset === "asset") return `asset:${animation.asset_animation_id}`;
  if (animation.preset === "rig") return `rig:${animation.rig_pose_id}`;
  return animation.preset;
}

function animationDisplayLabel(animation) {
  if (animation.preset === "asset") return animation.asset_animation_id;
  if (animation.preset === "rig") return animation.rig_pose_id;
  return animationLabels[animation.preset];
}

function easeAnimation(progress, easing) {
  if (easing === "linear") return progress;
  if (easing === "ease-in") return progress * progress;
  if (easing === "ease-out") return 1 - (1 - progress) ** 2;
  return progress < 0.5 ? 2 * progress * progress : 1 - (-2 * progress + 2) ** 2 / 2;
}

function evaluateAnimationClip(animation, time) {
  let progress = (time - animation.start_seconds) / animation.duration_seconds;
  if (animation.loop && progress >= 0) progress %= 1;
  else progress = Math.max(0, Math.min(1, progress));
  progress = easeAnimation(progress, animation.easing);
  if (animation.preset === "fade-in") return { x: 0, y: 0, scale: 1, rotation: 0, opacity: progress };
  if (animation.preset === "fade-out") return { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 - progress };
  if (animation.preset === "slide-in") {
    const distance = 180 * (1 - progress);
    const offset = { left: [-distance, 0], right: [distance, 0], up: [0, -distance], down: [0, distance] }[animation.direction];
    return { x: offset[0], y: offset[1], scale: 1, rotation: 0, opacity: 1 };
  }
  if (animation.preset === "bounce") return { x: 0, y: -55 * Math.sin(Math.PI * progress), scale: 1, rotation: 0, opacity: 1 };
  if (animation.preset === "float") return { x: 0, y: -24 * Math.sin(2 * Math.PI * progress), scale: 1, rotation: 0, opacity: 1 };
  if (animation.preset === "pulse") return { x: 0, y: 0, scale: 1 + 0.14 * Math.sin(Math.PI * progress), rotation: 0, opacity: 1 };
  if (animation.preset === "rotate") return { x: 0, y: 0, scale: 1, rotation: (animation.direction === "left" || animation.direction === "up" ? -1 : 1) * 360 * progress, opacity: 1 };
  if (animation.preset === "shake") return { x: 18 * Math.sin(8 * Math.PI * progress), y: 0, scale: 1, rotation: 0, opacity: 1 };
  return { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 };
}

function evaluateInstanceAnimations(instanceId, animations, time) {
  return animations.filter((item) => item.target === instanceId).reduce((combined, item) => {
    const current = evaluateAnimationClip(item, time);
    combined.x += current.x; combined.y += current.y; combined.scale *= current.scale;
    combined.rotation += current.rotation; combined.opacity *= current.opacity;
    return combined;
  }, { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 });
}

function contentAnimation(instance, animations, time) {
  const clips = animations.filter((item) => item.target === instance.id && ["asset", "rig"].includes(item.preset) && item.start_seconds <= time).sort((a, b) => (a.start_seconds - b.start_seconds) || a.id.localeCompare(b.id));
  return clips.at(-1) || null;
}

function assetAnimationFrame(instance, animations, time) {
  const clip = contentAnimation(instance, animations, time);
  if (clip?.preset !== "asset") return null;
  const asset = state.project.assets.find((item) => item.id === instance.asset_id);
  const capability = asset?.capabilities?.animations?.find((item) => item.id === clip.asset_animation_id);
  if (!capability) return null;
  const count = capability.type === "sprite_sheet" ? capability.frame_count : capability.frames.length;
  let frame = Math.floor((time - clip.start_seconds) * capability.fps);
  frame = clip.loop ? frame % count : Math.min(frame, count - 1);
  return { capability, frame };
}

function rigPoseState(instance, animations, time) {
  const clip = contentAnimation(instance, animations, time);
  if (clip?.preset !== "rig") return null;
  const asset = state.project.assets.find((item) => item.id === instance.asset_id);
  const rig = asset?.capabilities?.rig;
  const pose = rig?.poses?.find((item) => item.id === clip.rig_pose_id);
  if (!rig || !pose) return null;
  const elapsed = Math.max(0, time - clip.start_seconds);
  const progress = clip.loop ? (elapsed % clip.duration_seconds) / clip.duration_seconds : Math.min(1, elapsed / clip.duration_seconds);
  const rightIndex = Math.max(0, pose.keyframes.findIndex((keyframe) => keyframe.at >= progress));
  const leftIndex = Math.max(0, rightIndex - 1);
  const left = pose.keyframes[leftIndex];
  const right = pose.keyframes[rightIndex];
  const ratio = right.at === left.at ? 0 : (progress - left.at) / (right.at - left.at);
  const identity = { x: 0, y: 0, rotation: 0, scale: 1, opacity: 1 };
  const transforms = {};
  new Set([...Object.keys(left.transforms || {}), ...Object.keys(right.transforms || {})]).forEach((partId) => {
    const start = { ...identity, ...(left.transforms?.[partId] || {}) };
    const end = { ...identity, ...(right.transforms?.[partId] || {}) };
    transforms[partId] = Object.fromEntries(Object.keys(identity).map((field) => [field, start[field] + (end[field] - start[field]) * ratio]));
  });
  return { rig, pose, progress, transforms };
}

function rigPartMarkup(assetId, part, children, transforms) {
  const pose = { x: 0, y: 0, rotation: 0, scale: 1, opacity: 1, ...(transforms[part.id] || {}) };
  const scale = pose.scale === 1 ? "" : ` translate(${part.pivot_x} ${part.pivot_y}) scale(${pose.scale}) translate(${-part.pivot_x} ${-part.pivot_y})`;
  const descendants = (children.get(part.id) || []).sort((a, b) => (a.z_index - b.z_index) || a.id.localeCompare(b.id)).map((child) => rigPartMarkup(assetId, child, children, transforms)).join("");
  return `<g transform="translate(${part.x + pose.x} ${part.y + pose.y}) rotate(${pose.rotation} ${part.pivot_x} ${part.pivot_y})${scale}" opacity="${pose.opacity}" data-rig-part="${escapeHtml(part.id)}"><image href="${assetUrl(part.path)}" x="0" y="0" width="${part.width}" height="${part.height}"/>${descendants}</g>`;
}

function rigImageMarkup(instance, selected) {
  const children = new Map();
  selected.rig.parts.forEach((part) => {
    const parent = part.parent_id || null;
    if (!children.has(parent)) children.set(parent, []);
    children.get(parent).push(part);
  });
  const content = (children.get(null) || []).sort((a, b) => (a.z_index - b.z_index) || a.id.localeCompare(b.id)).map((part) => rigPartMarkup(instance.asset_id, part, children, selected.transforms)).join("");
  return `<svg x="0" y="0" width="${instance.width}" height="${instance.height}" viewBox="0 0 ${selected.rig.canvas_width} ${selected.rig.canvas_height}" preserveAspectRatio="none" data-rig-pose="${escapeHtml(selected.pose.id)}" data-rig-progress="${selected.progress.toFixed(6)}">${content}</svg>`;
}

function instanceImageMarkup(instance, asset, scene) {
  const rig = state.animationPreviewTime === null ? null : rigPoseState(instance, scene.animations, state.animationPreviewTime);
  if (rig) return rigImageMarkup(instance, rig);
  const selected = state.animationPreviewTime === null ? null : assetAnimationFrame(instance, scene.animations, state.animationPreviewTime);
  if (!selected) return `<image href="${assetUrl(asset.path)}" x="0" y="0" width="${instance.width}" height="${instance.height}" preserveAspectRatio="xMidYMid meet"/>`;
  const { capability, frame } = selected;
  if (capability.type === "frame_sequence") return `<image href="${assetUrl(capability.frames[frame])}" x="0" y="0" width="${instance.width}" height="${instance.height}" preserveAspectRatio="xMidYMid meet" data-asset-animation="${escapeHtml(capability.id)}" data-frame="${frame}"/>`;
  const columns = capability.columns;
  const rows = Math.ceil(capability.frame_count / columns);
  const sourceX = frame % columns * capability.frame_width;
  const sourceY = Math.floor(frame / columns) * capability.frame_height;
  return `<svg x="0" y="0" width="${instance.width}" height="${instance.height}" viewBox="${sourceX} ${sourceY} ${capability.frame_width} ${capability.frame_height}" preserveAspectRatio="none" data-asset-animation="${escapeHtml(capability.id)}" data-frame="${frame}"><image href="${assetUrl(capability.path)}" x="0" y="0" width="${capability.frame_width * columns}" height="${capability.frame_height * rows}"/></svg>`;
}

function renderComposer() {
  const ready = Boolean(state.project?.scenes?.length);
  $("#scene-notice").textContent = ready ? `${state.project.name} · drag an asset onto the stage` : "Choose a project to compose a scene.";
  $("#save-scene").disabled = !ready;
  $("#composer-scene-tabs").innerHTML = ready ? state.project.scenes.map((scene, index) => `<button class="${index === state.composerScene ? "active" : ""}" data-composer-scene="${index}">${escapeHtml(scene.id)}</button>`).join("") : "";
  const scene = currentProjectScene();
  normalizeSceneInstances(scene);
  const stage = $("#scene-stage");
  const base = '<defs><pattern id="stage-grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="#ffffff" stroke-opacity=".045" stroke-width="1"/></pattern></defs><rect width="1280" height="720" fill="#11121d"/><rect width="1280" height="720" fill="url(#stage-grid)"/>';
  if (!scene) { stage.innerHTML = base; renderInstanceInspector(); renderTimeline(); return; }
  const background = state.project.assets.find((asset) => asset.id === scene.background_asset_id);
  const backgroundSvg = background ? `<image href="${assetUrl(background.path)}" x="0" y="0" width="1280" height="720" preserveAspectRatio="xMidYMid slice"/>` : "";
  const instances = [...scene.instances].sort((a, b) => (a.z_index - b.z_index) || a.id.localeCompare(b.id));
  const instanceSvg = instances.map((instance) => {
    const asset = state.project.assets.find((item) => item.id === instance.asset_id);
    if (!asset) return "";
    const selected = instance.id === state.selectedInstance;
    const animation = state.animationPreviewTime === null ? { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1 } : evaluateInstanceAnimations(instance.id, scene.animations, state.animationPreviewTime);
    const opacity = instance.visible ? instance.opacity * animation.opacity : 0.2;
    const selection = selected ? `<rect class="selection-outline" x="0" y="0" width="${instance.width}" height="${instance.height}"/><circle class="resize-handle" data-resize="true" cx="${instance.width}" cy="${instance.height}" r="12"/>` : "";
    const centerX = instance.width / 2; const centerY = instance.height / 2;
    const scale = animation.scale === 1 ? "" : ` translate(${centerX} ${centerY}) scale(${animation.scale}) translate(${-centerX} ${-centerY})`;
    return `<g class="scene-instance${selected ? " selected" : ""}" data-instance-id="${escapeHtml(instance.id)}" transform="translate(${instance.x + animation.x} ${instance.y + animation.y}) rotate(${instance.rotation + animation.rotation} ${centerX} ${centerY})${scale}" opacity="${opacity}">${instanceImageMarkup(instance, asset, scene)}${selection}</g>`;
  }).join("");
  stage.innerHTML = `${base}${backgroundSvg}${instanceSvg}`;
  stage.classList.toggle("animation-previewing", state.animationPreviewTime !== null);
  renderInstanceInspector();
  renderTimeline();
}

function renderInstanceInspector() {
  const instance = instanceById(state.selectedInstance);
  $("#instance-controls").hidden = !instance;
  $("#empty-inspector").hidden = Boolean(instance);
  $("#instance-title").textContent = instance ? instance.id : "Nothing selected";
  if (!instance) return;
  $$('[data-instance-field]').forEach((input) => {
    const field = input.dataset.instanceField;
    if (field === "visible") input.checked = instance.visible;
    else input.value = instance[field];
  });
  const preset = $("#animation-preset");
  const previousPreset = preset.value;
  const choices = availableAnimations(instance);
  preset.innerHTML = choices.map((choice) => `<option value="${escapeHtml(choice.value)}">${escapeHtml(choice.label)}</option>`).join("");
  if (choices.some((choice) => choice.value === previousPreset)) preset.value = previousPreset;
  const animations = currentProjectScene().animations.filter((item) => item.target === instance.id);
  $("#animation-list").innerHTML = animations.map(animationCardTemplate).join("") || '<div class="empty-inspector">No animations on this object.</div>';
}

function animationCardTemplate(animation) {
  const choice = animationChoice(animation);
  const presets = availableAnimations(instanceById(animation.target)).map((item) => `<option value="${escapeHtml(item.value)}" ${choice === item.value ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("");
  const easings = ["linear", "ease-in", "ease-out", "ease-in-out"].map((name) => `<option value="${name}" ${animation.easing === name ? "selected" : ""}>${name}</option>`).join("");
  const directions = ["left", "right", "up", "down"].map((name) => `<option value="${name}" ${animation.direction === name ? "selected" : ""}>${name}</option>`).join("");
  return `<article class="animation-card" data-animation-id="${escapeHtml(animation.id)}"><div class="animation-card-head"><strong>${escapeHtml(animationDisplayLabel(animation))}</strong><button data-delete-animation title="Delete animation">×</button></div><div class="animation-card-grid"><label>Animation<select data-animation-field="choice">${presets}</select></label><label>Direction<select data-animation-field="direction">${directions}</select></label><label>Delay<input data-animation-field="start_seconds" type="number" min="0" step="0.1" value="${animation.start_seconds}"></label><label>Duration<input data-animation-field="duration_seconds" type="number" min="0.1" step="0.1" value="${animation.duration_seconds}"></label><label>Easing<select data-animation-field="easing">${easings}</select></label><label class="visibility-control"><input data-animation-field="loop" type="checkbox" ${animation.loop ? "checked" : ""}> Loop</label></div></article>`;
}

function registerProjectAsset(path) {
  let asset = state.project.assets.find((item) => item.path === path);
  if (asset) return asset;
  const category = path.split("/")[0];
  const kind = { characters: "character", scenes: "scene", props: "prop", audio: "audio", music: "music" }[category] || "prop";
  const filename = path.split("/").pop().replace(/\.[^.]+$/, "");
  const id = uniqueId(filename, new Set(state.project.assets.map((item) => item.id)));
  asset = { id, kind, path };
  state.project.assets.push(asset);
  return asset;
}

function stagePoint(event) {
  const bounds = $("#scene-stage").getBoundingClientRect();
  return { x: (event.clientX - bounds.left) * 1280 / bounds.width, y: (event.clientY - bounds.top) * 720 / bounds.height };
}

function dropAssetOnStage(event) {
  event.preventDefault();
  $(".stage-shell").classList.remove("drag-over");
  if (!currentProjectScene()) return toast("Open a project first", true);
  const path = event.dataTransfer.getData("application/x-al-studio-asset") || event.dataTransfer.getData("text/plain");
  if (!path || !state.composerAssets.some((asset) => asset.path === path)) return;
  const asset = registerProjectAsset(path);
  const point = stagePoint(event);
  const isCharacter = asset.kind === "character";
  const width = isCharacter ? 260 : 220;
  const height = isCharacter ? 390 : 190;
  const scene = currentProjectScene();
  const id = uniqueId(asset.id, new Set(scene.instances.map((item) => item.id)));
  const topLayer = Math.max(-1, ...scene.instances.map((item) => item.z_index)) + 1;
  scene.instances.push({ id, asset_id: asset.id, x: Math.max(0, Math.min(1280 - width, point.x - width / 2)), y: Math.max(0, Math.min(720 - height, point.y - height / 2)), width, height, rotation: 0, opacity: 1, z_index: topLayer, visible: true });
  state.selectedInstance = id;
  renderComposer();
}

function beginStagePointer(event) {
  const object = event.target.closest(".scene-instance");
  if (!object) { state.selectedInstance = ""; renderComposer(); return; }
  state.selectedInstance = object.dataset.instanceId;
  const instance = instanceById(state.selectedInstance);
  const point = stagePoint(event);
  state.pointerDrag = { mode: event.target.dataset.resize ? "resize" : "move", startX: point.x, startY: point.y, x: instance.x, y: instance.y, width: instance.width, height: instance.height };
  renderComposer();
  event.preventDefault();
}

function moveStagePointer(event) {
  if (!state.pointerDrag) return;
  const instance = instanceById(state.selectedInstance);
  if (!instance) return;
  const point = stagePoint(event);
  const dx = point.x - state.pointerDrag.startX;
  const dy = point.y - state.pointerDrag.startY;
  if (state.pointerDrag.mode === "move") {
    instance.x = Math.round(Math.max(0, Math.min(1280 - instance.width, state.pointerDrag.x + dx)));
    instance.y = Math.round(Math.max(0, Math.min(720 - instance.height, state.pointerDrag.y + dy)));
  } else {
    instance.width = Math.round(Math.max(30, Math.min(1280 - instance.x, state.pointerDrag.width + dx)));
    instance.height = Math.round(Math.max(30, Math.min(720 - instance.y, state.pointerDrag.height + dy)));
  }
  renderComposer();
}

function editInstance(event) {
  const instance = instanceById(state.selectedInstance);
  if (!instance) return;
  const field = event.target.dataset.instanceField;
  if (!field) return;
  instance[field] = field === "visible" ? event.target.checked : Number(event.target.value);
  if (["width", "height"].includes(field)) instance[field] = Math.max(1, instance[field]);
  if (field === "opacity") instance.opacity = Math.max(0, Math.min(1, instance.opacity));
  renderComposer();
}

function changeLayer(direction) {
  const instance = instanceById(state.selectedInstance);
  const scene = currentProjectScene();
  if (!instance || !scene) return;
  const ordered = [...scene.instances].sort((a, b) => (a.z_index - b.z_index) || a.id.localeCompare(b.id));
  const index = ordered.indexOf(instance);
  const other = ordered[direction === "front" ? index + 1 : index - 1];
  if (!other) return;
  const layer = instance.z_index;
  instance.z_index = other.z_index;
  other.z_index = layer;
  if (instance.z_index === other.z_index) instance.z_index += direction === "front" ? 1 : -1;
  renderComposer();
}

function addAnimation() {
  const scene = currentProjectScene();
  const instance = instanceById(state.selectedInstance);
  if (!scene || !instance) return;
  const duration = Number($("#animation-duration").value);
  const start = Number($("#animation-start").value);
  if (!(duration > 0) || start < 0) return toast("Animation delay must be zero or more and duration must be positive", true);
  const choice = $("#animation-preset").value;
  const assetAnimationId = choice.startsWith("asset:") ? choice.slice(6) : null;
  const rigPoseId = choice.startsWith("rig:") ? choice.slice(4) : null;
  const preset = assetAnimationId ? "asset" : rigPoseId ? "rig" : choice;
  const capability = state.project.assets.find((item) => item.id === instance.asset_id)?.capabilities?.animations?.find((item) => item.id === assetAnimationId);
  const pose = state.project.assets.find((item) => item.id === instance.asset_id)?.capabilities?.rig?.poses?.find((item) => item.id === rigPoseId);
  const id = uniqueId(`${instance.id}-${assetAnimationId || rigPoseId || preset}`, new Set(scene.animations.map((item) => item.id)));
  const animation = { id, target: instance.id, preset, start_seconds: start, duration_seconds: duration, easing: $("#animation-easing").value, direction: $("#animation-direction").value, loop: assetAnimationId ? capability?.loop ?? true : rigPoseId ? pose?.loop ?? false : $("#animation-loop").checked };
  if (assetAnimationId) animation.asset_animation_id = assetAnimationId;
  if (rigPoseId) animation.rig_pose_id = rigPoseId;
  scene.animations.push(animation);
  renderComposer();
  toast("Animation added — preview or save the scene");
}

function applyAnimationChoiceDefaults() {
  const instance = instanceById(state.selectedInstance);
  const choice = $("#animation-preset").value;
  if (!instance) return;
  const asset = state.project.assets.find((item) => item.id === instance.asset_id);
  if (choice.startsWith("asset:")) {
    const capability = asset?.capabilities?.animations?.find((item) => item.id === choice.slice(6));
    if (!capability) return;
    const frames = capability.type === "sprite_sheet" ? capability.frame_count : capability.frames.length;
    $("#animation-duration").value = Math.max(0.1, frames / capability.fps).toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
    $("#animation-loop").checked = capability.loop ?? true;
  } else if (choice.startsWith("rig:")) {
    const pose = asset?.capabilities?.rig?.poses?.find((item) => item.id === choice.slice(4));
    if (!pose) return;
    $("#animation-duration").value = pose.duration_seconds ?? 1;
    $("#animation-loop").checked = pose.loop ?? false;
  }
}

function editAnimation(event) {
  if (event.type === "click" && event.target.dataset.deleteAnimation === undefined) return;
  const card = event.target.closest("[data-animation-id]");
  if (!card) return;
  const scene = currentProjectScene();
  const animation = scene.animations.find((item) => item.id === card.dataset.animationId);
  if (!animation) return;
  if (event.target.dataset.deleteAnimation !== undefined) {
    scene.animations = scene.animations.filter((item) => item.id !== animation.id);
    renderComposer();
    return;
  }
  const field = event.target.dataset.animationField;
  if (!field) return;
  if (field === "choice") {
    const choice = event.target.value;
    if (choice.startsWith("asset:")) {
      animation.preset = "asset";
      animation.asset_animation_id = choice.slice(6);
      delete animation.rig_pose_id;
      const instance = instanceById(animation.target);
      const capability = state.project.assets.find((item) => item.id === instance.asset_id)?.capabilities?.animations?.find((item) => item.id === animation.asset_animation_id);
      animation.loop = capability?.loop ?? true;
    } else if (choice.startsWith("rig:")) {
      animation.preset = "rig";
      animation.rig_pose_id = choice.slice(4);
      delete animation.asset_animation_id;
      const instance = instanceById(animation.target);
      const pose = state.project.assets.find((item) => item.id === instance.asset_id)?.capabilities?.rig?.poses?.find((item) => item.id === animation.rig_pose_id);
      animation.loop = pose?.loop ?? false;
      animation.duration_seconds = pose?.duration_seconds ?? animation.duration_seconds;
    } else {
      animation.preset = choice;
      delete animation.asset_animation_id;
      delete animation.rig_pose_id;
    }
    renderComposer();
    return;
  }
  animation[field] = field === "loop" ? event.target.checked : ["start_seconds", "duration_seconds"].includes(field) ? Number(event.target.value) : event.target.value;
  if (animation.start_seconds < 0) animation.start_seconds = 0;
  if (animation.duration_seconds <= 0) animation.duration_seconds = 0.1;
  renderComposer();
}

function stopAnimationPreview() {
  if (state.animationPreviewFrame !== null) cancelAnimationFrame(state.animationPreviewFrame);
  state.animationPreviewFrame = null;
  state.animationPreviewTime = null;
  $("#preview-animations").textContent = "▶";
  renderComposer();
}

function previewAnimations() {
  const scene = currentProjectScene();
  if (!scene?.animations?.length) return toast("Add an animation to preview", true);
  if (state.animationPreviewTime !== null) { stopAnimationPreview(); return; }
  const duration = Math.min(12, Math.max(2, sceneTimelineData(scene).duration));
  const started = performance.now();
  $("#preview-animations").textContent = "■";
  const tick = (now) => {
    state.animationPreviewTime = (now - started) / 1000;
    renderComposer();
    if (state.animationPreviewTime >= duration) stopAnimationPreview();
    else state.animationPreviewFrame = requestAnimationFrame(tick);
  };
  state.animationPreviewFrame = requestAnimationFrame(tick);
}

function deleteSelectedInstance() {
  const scene = currentProjectScene();
  if (!scene || !state.selectedInstance) return;
  scene.instances = scene.instances.filter((instance) => instance.id !== state.selectedInstance);
  scene.animations = scene.animations.filter((animation) => animation.target !== state.selectedInstance);
  state.selectedInstance = "";
  renderComposer();
}

async function saveScene() {
  if (!state.projectName) return toast("Open a project first", true);
  try {
    await api(`/api/projects/${encodeURIComponent(state.projectName)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: state.project }) });
    toast("Scene layout saved");
  } catch (error) { toast(error.message, true); }
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
  renderTimeline();
}

function blockTemplate(event, index) {
  const type = event.type;
  const speakers = state.project.characters || [];
  const start = event.start_seconds ?? "";
  const startField = `<label>Start (seconds)<input data-field="start_seconds" type="number" min="0" step="0.1" value="${escapeHtml(start)}" placeholder="Auto"></label>`;
  let fields;
  if (type === "dialogue") {
    fields = `<label>Speaker<select data-field="speaker">${speakers.map((character) => `<option ${character.name === event.speaker ? "selected" : ""}>${escapeHtml(character.name)}</option>`).join("")}</select></label><label>Dialogue<input data-field="text" value="${escapeHtml(event.text)}"></label>${startField}<label>Duration<input value="Auto from voice" disabled></label><label class="full">Caption<input data-field="caption" value="${escapeHtml(event.caption || "")}" placeholder="Defaults to dialogue text"></label>`;
  } else if (["ambience", "sound_effect"].includes(type)) {
    const assets = (state.project.assets || []).filter((asset) => ["audio", "music"].includes(asset.kind));
    fields = `<label class="full">Audio asset<select data-field="asset_id">${assets.map((asset) => `<option value="${escapeHtml(asset.id)}" ${asset.id === event.asset_id ? "selected" : ""}>${escapeHtml(asset.id)} · ${escapeHtml(asset.path)}</option>`).join("") || '<option value="">Import an audio asset first</option>'}</select></label>${startField}<label>Duration (seconds)<input data-field="duration_seconds" type="number" min="0.1" step="0.1" value="${escapeHtml(event.duration_seconds || 1)}"></label>`;
  } else {
    const textKey = type === "caption" ? "text" : "description";
    fields = `<label class="full">${type === "caption" ? "Caption" : "Action"}<input data-field="${textKey}" value="${escapeHtml(event[textKey] || "")}" placeholder="Describe this ${type}"></label>${startField}<label>Duration (seconds)<input data-field="duration_seconds" type="number" min="0.1" step="0.1" value="${escapeHtml(event.duration_seconds || 1)}"></label>`;
  }
  return `<article class="script-block" data-index="${index}"><span class="drag">⠿</span><span class="type-pill">${escapeHtml(type)}</span><div class="block-fields">${fields}</div><div class="block-actions"><button data-move="up" title="Move up">↑</button><button data-move="down" title="Move down">↓</button><button data-delete title="Delete">×</button></div></article>`;
}

function editBlock(event) {
  const block = event.target.closest(".script-block");
  if (!block) return;
  const item = currentScene().events[Number(block.dataset.index)];
  const field = event.target.dataset.field;
  if (!field) return;
  if (field === "start_seconds" && event.target.value === "") delete item.start_seconds;
  else item[field] = ["duration_seconds", "start_seconds"].includes(field) ? Number(event.target.value) : event.target.value;
  renderTimeline();
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
  if (["ambience", "sound_effect"].includes(type)) {
    const asset = (state.project.assets || []).find((item) => ["audio", "music"].includes(item.kind));
    scene.events.push({ type, asset_id: asset?.id || "", duration_seconds: type === "ambience" ? 5 : 1 });
  }
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
    const visualAssets = (state.project?.assets || []).filter((asset) => ["character", "scene", "prop"].includes(asset.kind));
    $("#capability-asset").innerHTML = '<option value="">Choose a project asset</option>' + visualAssets.map((asset) => { const animations = (asset.capabilities?.animations || []).length; const poses = (asset.capabilities?.rig?.poses || []).length; return `<option value="${escapeHtml(asset.id)}">${escapeHtml(asset.id)} · ${animations} frame animation${animations === 1 ? "" : "s"} · ${poses} rig pose${poses === 1 ? "" : "s"}</option>`; }).join("");
  } catch (error) { toast(error.message, true); }
}

async function importAsset() {
  const files = [...$("#asset-file").files];
  if (!files.length) return toast("Choose one or more files to import", true);
  const category = $("#asset-category").value;
  const button = $("#import-asset");
  button.disabled = true;
  try {
    for (const file of files) {
      const imported = await api(`/api/assets/${category}?filename=${encodeURIComponent(file.name)}`, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file });
      if (state.project && ["audio", "music"].includes(category)) registerProjectAsset(imported.path);
    }
    if (state.project && ["audio", "music"].includes(category)) {
      await api(`/api/projects/${encodeURIComponent(state.projectName)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: state.project }) });
      renderScript();
    }
    $("#asset-file").value = "";
    toast(`Imported ${files.length} asset${files.length === 1 ? "" : "s"}`);
    await loadAssets();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function attachCapabilities() {
  if (!state.projectName) return toast("Open a project first", true);
  const assetId = $("#capability-asset").value;
  const file = $("#capability-file").files[0];
  if (!assetId || !file) return toast("Choose a visual asset and manifest JSON", true);
  try {
    const manifest = JSON.parse(await file.text());
    if (!manifest || typeof manifest !== "object" || (!Array.isArray(manifest.animations) && typeof manifest.rig !== "object")) throw new Error("Manifest must contain animations, a rig, or both");
    if (manifest.animations === undefined) manifest.animations = [];
    const asset = state.project.assets.find((item) => item.id === assetId);
    const previous = asset.capabilities;
    asset.capabilities = manifest;
    try {
      await api(`/api/projects/${encodeURIComponent(state.projectName)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: state.project }) });
    } catch (error) {
      if (previous === undefined) delete asset.capabilities;
      else asset.capabilities = previous;
      throw error;
    }
    $("#capability-file").value = "";
    const poseCount = manifest.rig?.poses?.length || 0;
    toast(`Attached ${manifest.animations.length} frame animations and ${poseCount} rig poses to ${assetId}`);
    await loadAssets();
    renderComposer();
  } catch (error) { toast(error.message, true); }
}

function editableCreativeDraft() {
  const value = $("#creative-result").value.trim();
  if (!value) throw new Error("Generate or enter a draft first");
  const draft = JSON.parse(value);
  if (!draft || typeof draft !== "object" || Array.isArray(draft)) throw new Error("Draft must be a JSON object");
  return draft;
}

async function generateCreativeDraft() {
  if (!state.projectName) return toast("Open a project first", true);
  const prompt = $("#creative-prompt").value.trim();
  if (!prompt) return toast("Describe what you want to explore", true);
  const button = $("#generate-creative");
  button.disabled = true;
  try {
    const kind = $("#creative-kind").value;
    const result = await api(`/api/projects/${encodeURIComponent(state.projectName)}/creative`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind, prompt }) });
    state.creativeKind = result.kind;
    $("#creative-result").value = JSON.stringify(result.draft, null, 2);
    $("#creative-result-title").textContent = `${result.kind.replace(/^./, (letter) => letter.toUpperCase())} draft`;
    $("#creative-provider").textContent = `${result.provider} · optional · not used by rendering`;
    $("#creative-dirty-state").textContent = "Editable · not saved";
    $("#save-creative").disabled = false;
    $("#apply-creative").disabled = false;
    toast("Editable creative draft generated");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function saveCreativeDraft() {
  if (!state.projectName) return toast("Open a project first", true);
  try {
    const draft = editableCreativeDraft();
    const kind = state.creativeKind || $("#creative-kind").value;
    const saved = await api(`/api/projects/${encodeURIComponent(state.projectName)}/creative/save`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kind, draft }) });
    $("#creative-dirty-state").textContent = `Saved · ${saved.name}`;
    await loadCreativeDrafts();
    toast("Reusable creative draft saved");
    return saved;
  } catch (error) { toast(error.message, true); return null; }
}

async function applyCreativeDraft() {
  if (!state.projectName) return toast("Open a project first", true);
  try {
    const draft = editableCreativeDraft();
    const kind = state.creativeKind || $("#creative-kind").value;
    if (kind === "script") {
      if (!Array.isArray(draft.events)) throw new Error("Script draft requires an events list");
      const target = state.script.scenes.find((scene) => scene.scene_id === draft.scene_id) || state.script.scenes[0];
      if (!target) throw new Error("Project script has no scene to receive the draft");
      const previous = [...target.events];
      target.events.push(...draft.events);
      try { await api(`/api/projects/${encodeURIComponent(state.projectName)}/script`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: state.script }) }); }
      catch (error) { target.events = previous; throw error; }
      state.scene = state.script.scenes.indexOf(target);
      renderScript(); showView("script");
      toast("Script draft applied and saved");
      return;
    }
    if (kind === "character") {
      const character = draft.character;
      if (!character?.name || !character?.voice_id) throw new Error("Character draft requires name and voice_id");
      state.project.characters ||= [];
      if (state.project.characters.some((item) => item.name === character.name)) throw new Error(`Character already exists: ${character.name}`);
      const config = { name: character.name, voice_id: character.voice_id, animation: { idle_motion: true, mouth_style: "simple" } };
      state.project.characters.push(config);
      try { await api(`/api/projects/${encodeURIComponent(state.projectName)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: state.project }) }); }
      catch (error) { state.project.characters.pop(); throw error; }
      toast(`Character ${character.name} applied to project`);
      return;
    }
    if (await saveCreativeDraft()) toast("Concept attached to the project’s reusable draft library");
  } catch (error) { toast(error.message, true); }
}

async function loadCreativeDrafts() {
  const node = $("#creative-saved");
  if (!state.projectName) { node.innerHTML = '<div class="notice">Open a project to view its saved drafts.</div>'; return; }
  try {
    const drafts = await api(`/api/projects/${encodeURIComponent(state.projectName)}/creative`);
    node.innerHTML = drafts.map((draft) => `<article class="asset-card"><div class="asset-icon">◈</div><h3>${escapeHtml(draft.name)}</h3><p>${escapeHtml(draft.path)}</p></article>`).join("") || '<div class="notice">No creative drafts saved yet.</div>';
  } catch (error) { toast(error.message, true); }
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
  $("#composer-scene-tabs").addEventListener("click", (event) => { if (event.target.dataset.composerScene !== undefined) { if (state.animationPreviewTime !== null) stopAnimationPreview(); state.composerScene = Number(event.target.dataset.composerScene); state.selectedInstance = ""; renderComposer(); } });
  $("#composer-asset-search").addEventListener("input", renderComposerAssetTray);
  $("#refresh-composer-assets").addEventListener("click", loadComposerAssets);
  $("#composer-asset-list").addEventListener("dragstart", (event) => { const item = event.target.closest("[data-asset-path]"); if (item) { event.dataTransfer.setData("application/x-al-studio-asset", item.dataset.assetPath); event.dataTransfer.setData("text/plain", item.dataset.assetPath); } });
  $(".stage-shell").addEventListener("dragover", (event) => { event.preventDefault(); $(".stage-shell").classList.add("drag-over"); });
  $(".stage-shell").addEventListener("dragleave", () => $(".stage-shell").classList.remove("drag-over"));
  $(".stage-shell").addEventListener("drop", dropAssetOnStage);
  $("#scene-stage").addEventListener("pointerdown", beginStagePointer);
  document.addEventListener("pointermove", moveStagePointer);
  document.addEventListener("pointerup", () => { state.pointerDrag = null; });
  $("#instance-controls").addEventListener("input", editInstance);
  $("#instance-controls").addEventListener("click", (event) => { if (event.target.dataset.layer) changeLayer(event.target.dataset.layer); });
  $("#add-animation").addEventListener("click", addAnimation);
  $("#animation-preset").addEventListener("change", applyAnimationChoiceDefaults);
  $("#preview-animations").addEventListener("click", previewAnimations);
  $("#animation-list").addEventListener("change", editAnimation);
  $("#animation-list").addEventListener("click", editAnimation);
  $("#delete-instance").addEventListener("click", deleteSelectedInstance);
  $("#save-scene").addEventListener("click", saveScene);
  $("#scene-tabs").addEventListener("click", (event) => { if (event.target.dataset.scene !== undefined) { state.scene = Number(event.target.dataset.scene); const sceneId = currentScene()?.scene_id; const projectIndex = state.project?.scenes?.findIndex((scene) => scene.id === sceneId) ?? -1; if (projectIndex >= 0) state.composerScene = projectIndex; renderScript(); } });
  $("#block-list").addEventListener("input", editBlock); $("#block-list").addEventListener("click", actOnBlock);
  $("#add-row").addEventListener("click", (event) => { if (event.target.dataset.add) addBlock(event.target.dataset.add); });
  $("#save-script").addEventListener("click", saveScript);
  $("#import-asset").addEventListener("click", importAsset);
  $("#attach-capabilities").addEventListener("click", attachCapabilities);
  $("#asset-file").addEventListener("change", (event) => { const file = event.target.files[0]; if (file) $(".file-drop strong").textContent = file.name; });
  $("#preview-voice").addEventListener("click", previewVoice);
  $("#generate-creative").addEventListener("click", generateCreativeDraft);
  $("#save-creative").addEventListener("click", saveCreativeDraft);
  $("#apply-creative").addEventListener("click", applyCreativeDraft);
  $("#refresh-creative").addEventListener("click", loadCreativeDrafts);
  $("#creative-result").addEventListener("input", () => { if (!$("#save-creative").disabled) $("#creative-dirty-state").textContent = "Edited · not saved"; });
  $("#validate-project").addEventListener("click", validateProject);
  $("#dry-run").addEventListener("click", () => startRender(true));
  $("#start-render").addEventListener("click", () => startRender(false));
  showView(location.hash.slice(1) in titles ? location.hash.slice(1) : "projects");
  try { await loadProjects(); } catch (error) { toast(error.message, true); }
});
