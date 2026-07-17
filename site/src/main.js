import { getStudentIndex, mediaUrl } from "./data.js";
import {
  UI_STRINGS, applyStrings, currentLang, initLangToggle, watchReveals,
} from "./shared.js";

async function boot() {
  const lang = currentLang();
  applyStrings(lang);
  initLangToggle((l) => { applyStrings(l); renderCards(l); });

  let index;
  try {
    index = await getStudentIndex();
  } catch {
    document.getElementById("studentGrid").innerHTML =
      "<p class='text-ink-soft'>Journals are being prepared…</p>";
    return;
  }
  window.__students = index.students;
  renderCards(lang);
}

function renderCards(lang) {
  const grid = document.getElementById("studentGrid");
  grid.innerHTML = "";
  (window.__students || []).forEach((s, i) => {
    const a = document.createElement("a");
    a.className = "student-card reveal";
    a.style.transitionDelay = `${(i % 3) * 80}ms`;
    a.href = `./student.html?s=${encodeURIComponent(s.slug)}`;
    a.innerHTML = `
      <img loading="lazy" decoding="async" alt="" />
      <div class="veil"></div>
      <div class="absolute bottom-0 inset-x-0 p-6 text-white">
        <p class="font-display text-2xl"></p>
        <p class="text-[0.65rem] tracking-[0.25em] uppercase opacity-80 mt-1"></p>
      </div>`;
    a.querySelector("img").src = mediaUrl(s.thumb);
    a.querySelector(".font-display").textContent = s.name;
    a.querySelector("p:last-child").textContent =
      `${s.class ? s.class + " · " : ""}${UI_STRINGS[lang].open}`;
    grid.appendChild(a);
  });
  watchReveals();
}

boot();
