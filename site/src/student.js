import ColorThief from "colorthief";
import { getStudent, mediaUrl } from "./data.js";
import {
  applyStrings, currentLang, initLangToggle, initTopbarTint, watchReveals,
} from "./shared.js";

const $ = (id) => document.getElementById(id);

/* ---------- palette: pick an elegant accent from the hero image ---------- */

function rgbToHsl([r, g, b]) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h;
  switch (max) {
    case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
    case g: h = ((b - r) / d + 2) / 6; break;
    default: h = ((r - g) / d + 4) / 6;
  }
  return [h, s, l];
}

function hslCss(h, s, l) {
  return `hsl(${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%)`;
}

function applyPalette(img) {
  try {
    const palette = new ColorThief().getPalette(img, 8);
    let best = null, bestScore = -1;
    for (const rgb of palette) {
      const [h, s, l] = rgbToHsl(rgb);
      const score = s * (1 - Math.abs(l - 0.45) * 1.6);
      if (score > bestScore) { bestScore = score; best = [h, s, l]; }
    }
    if (!best) return;
    let [h, s, l] = best;
    s = Math.min(s, 0.62);                       // keep it muted / luxurious
    l = Math.min(Math.max(l, 0.32), 0.52);
    const root = document.documentElement.style;
    root.setProperty("--accent", hslCss(h, s, l));
    root.setProperty("--accent-deep", hslCss(h, Math.min(s + 0.05, 0.7), Math.max(l - 0.16, 0.16)));
    root.setProperty("--accent-wash", `hsl(${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}% / 0.07)`);
  } catch { /* palette extraction is a nicety, never fatal */ }
}

/* ---------- render ---------- */

let student;

function renderHero() {
  const wrap = $("heroMediaWrap");
  wrap.innerHTML = "";
  const { hero } = student;
  const posterUrl = mediaUrl(hero.poster || hero.src);

  if (hero.type === "video") {
    const v = document.createElement("video");
    v.className = "hero-media";
    v.src = mediaUrl(hero.src);
    v.poster = posterUrl;
    v.muted = true; v.loop = true; v.autoplay = true; v.playsInline = true;
    wrap.appendChild(v);
  } else {
    const img = document.createElement("img");
    img.className = "hero-media";
    img.src = posterUrl;
    img.alt = student.name;
    wrap.appendChild(img);
  }

  // palette source is always the still poster
  const probe = new Image();
  probe.crossOrigin = "anonymous";
  probe.src = posterUrl;
  if (probe.complete) applyPalette(probe);
  else probe.addEventListener("load", () => applyPalette(probe));
}

function hasRemarks() {
  const r = student.remarks || {};
  return Boolean(r.en?.narrative?.length || r.vi?.narrative?.length);
}

function renumberSections() {
  let n = 0;
  document.querySelectorAll("main section").forEach((sec) => {
    if (sec.style.display === "none") return;
    const no = sec.querySelector(".section-no");
    if (no) no.textContent = String(++n).padStart(2, "0");
  });
}

function renderInterviews() {
  const grid = $("interviewGrid");
  grid.innerHTML = "";
  const vids = student.interviews || [];
  $("interviewSection").style.display = vids.length ? "" : "none";
  grid.className = vids.length > 1 ? "grid md:grid-cols-2 gap-6" : "grid gap-6 max-w-3xl";
  for (const v of vids) {
    const wrap = document.createElement("div");
    wrap.className = "reveal";
    wrap.innerHTML = `
      <div class="aspect-video overflow-hidden rounded-sm bg-ink">
        <iframe class="w-full h-full" loading="lazy"
          src="https://www.youtube-nocookie.com/embed/${v.youtubeId}?rel=0"
          title="${v.title || student.name}"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
      </div>`;
    grid.appendChild(wrap);
  }
}

function renderText(lang) {
  const r = student.remarks?.[lang] || student.remarks?.en || {};
  document.title = `${student.name} — Summer Journal · HEC`;
  $("studentName").textContent = student.displayName || student.name;

  $("heroMeta").innerHTML = "";
  const metaBits = [student.camp?.class, student.camp?.dates].filter(Boolean);
  for (const bit of metaBits) {
    const span = document.createElement("span");
    span.className = "border-l border-white/30 pl-3 first:border-0 first:pl-0";
    span.textContent = bit;
    $("heroMeta").appendChild(span);
  }

  const withRemarks = hasRemarks();
  $("remarkHeadline").textContent = r.headline || "";
  const body = $("remarkBody");
  body.innerHTML = "";
  for (const p of r.narrative || []) {
    const el = document.createElement("p");
    el.className = "reveal";
    el.textContent = p;
    body.appendChild(el);
  }
  $("teacherSign").textContent = r.signature || "Happy English Club";
  // no written reflection yet: keep the page alive, promise the words
  $("teacherSignWrap").style.display = withRemarks ? "" : "none";
  $("remarksPending").classList.toggle("hidden", withRemarks);

  const cards = $("strengthCards");
  cards.innerHTML = "";
  (r.strengths || []).forEach((s, i) => {
    const card = document.createElement("article");
    card.className = "strength-card reveal";
    card.style.transitionDelay = `${i * 90}ms`;
    card.innerHTML = `
      <p class="attr text-[0.65rem] tracking-[0.3em] uppercase font-medium"></p>
      <h3 class="font-display text-xl mt-3 mb-3"></h3>
      <p class="text-sm text-ink-soft leading-relaxed"></p>`;
    card.querySelector(".attr").textContent = s.attribute || "";
    card.querySelector("h3").textContent = s.title || "";
    card.querySelector("p.text-sm").textContent = s.body || "";
    cards.appendChild(card);
  });
  $("strengthsSection").style.display = (r.strengths || []).length ? "" : "none";

  const stats = $("statGrid");
  stats.innerHTML = "";
  for (const s of student.stats?.[lang] || student.stats?.en || []) {
    const div = document.createElement("div");
    div.className = "reveal";
    div.innerHTML = `<p class="stat-value"></p>
      <p class="text-[0.65rem] tracking-[0.25em] uppercase text-ink-soft mt-2"></p>`;
    div.querySelector(".stat-value").textContent = s.value;
    div.querySelector("p:last-child").textContent = s.label;
    stats.appendChild(div);
  }
  $("statBand").style.display = (student.stats?.en || []).length ? "" : "none";

  const next = $("nextSteps");
  next.innerHTML = "";
  for (const p of r.nextSteps || []) {
    const el = document.createElement("p");
    el.textContent = p;
    next.appendChild(el);
  }
  $("nextSection").style.display = (r.nextSteps || []).length ? "" : "none";

  applyStrings(lang);
  renumberSections();
  watchReveals();
}

function renderGallery() {
  const gallery = $("gallery");
  gallery.innerHTML = "";
  const items = student.gallery || [];
  $("galleryCount").textContent = `${items.length} moments`;
  if (items.length <= 4) gallery.classList.add("masonry-wide");

  items.forEach((item, i) => {
    const tile = document.createElement("figure");
    tile.className = "tile reveal";
    tile.style.transitionDelay = `${(i % 3) * 70}ms`;
    if (item.type === "video") {
      tile.innerHTML = `
        <video preload="metadata" muted playsinline ${item.poster ? `poster="${mediaUrl(item.poster)}"` : ""}
               src="${mediaUrl(item.src)}"></video>
        <div class="play-badge"><span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l11-6.5z"/></svg>
        </span></div>`;
    } else {
      tile.innerHTML = `<img loading="lazy" decoding="async"
        src="${mediaUrl(item.src)}" alt="${student.name} at HEC summer camp"
        ${item.w && item.h ? `width="${item.w}" height="${item.h}"` : ""} />`;
    }
    tile.addEventListener("click", () => openLightbox(item));
    gallery.appendChild(tile);
  });
  watchReveals();
}

/* ---------- lightbox ---------- */

function openLightbox(item) {
  const box = $("lightbox");
  const content = $("lightboxContent");
  content.innerHTML = "";
  if (item.type === "video") {
    const v = document.createElement("video");
    v.src = mediaUrl(item.src);
    v.controls = true; v.autoplay = true; v.playsInline = true;
    content.appendChild(v);
  } else {
    const img = document.createElement("img");
    img.src = mediaUrl(item.src);
    content.appendChild(img);
  }
  box.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  const box = $("lightbox");
  box.classList.remove("open");
  $("lightboxContent").innerHTML = "";
  document.body.style.overflow = "";
}

/* ---------- boot ---------- */

async function boot() {
  const slug = new URLSearchParams(location.search).get("s");
  if (!slug) { location.replace("./index.html"); return; }
  try {
    student = await getStudent(slug);
  } catch {
    document.body.innerHTML =
      "<p style='padding:4rem;font-family:sans-serif'>Journal not found. <a href='./index.html'>Back</a></p>";
    return;
  }
  renderHero();
  renderInterviews();
  renderText(currentLang());
  renderGallery();
  initTopbarTint();
  initLangToggle((lang) => renderText(lang));

  $("lightbox").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeLightbox();
  });
  $("lightboxClose").addEventListener("click", closeLightbox);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeLightbox();
  });
}

boot();
