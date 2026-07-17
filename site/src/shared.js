/** Shared UI behaviours: scroll reveal, language toggle, topbar tint. */

export const UI_STRINGS = {
  en: {
    heroKicker: "Summer Camp 2026 · Student Journal",
    narrativeKicker: "The Journey",
    interviewKicker: "In Their Own Words",
    pendingRemarks: "The teacher's written reflection is being prepared with care — it will appear here soon.",
    strengthsKicker: "Signature Strengths",
    galleryKicker: "Moments in the Making",
    nextKicker: "The Path Ahead",
    teacherRole: "The HEC Teaching Team",
    cta: "Continue the journey at HEC",
    footerTag: "Small classes, big confidence. A US-licensed teacher, Oxford & Cambridge curriculum, and no more than 12 students per class.",
    footerNote: "This journal is a private keepsake prepared for the family.",
    indexKicker: "Happy English Club · Hà Nội",
    indexTitle: "Summer Camp 2026",
    indexSub: "A private journal of each camper's journey — their projects, their breakthroughs, and the moments that made this summer matter.",
    open: "Open journal",
  },
  vi: {
    heroKicker: "Trại Hè 2026 · Nhật Ký Học Viên",
    narrativeKicker: "Hành Trình",
    interviewKicker: "Con Tự Kể",
    pendingRemarks: "Nhận xét của giáo viên đang được chăm chút hoàn thiện — sẽ sớm xuất hiện tại đây.",
    strengthsKicker: "Điểm Mạnh Nổi Bật",
    galleryKicker: "Những Khoảnh Khắc",
    nextKicker: "Chặng Đường Phía Trước",
    teacherRole: "Đội ngũ giáo viên HEC",
    cta: "Tiếp tục hành trình cùng HEC",
    footerTag: "Lớp học nhỏ, tự tin lớn. Giáo viên Mỹ có bằng sư phạm, giáo trình Oxford & Cambridge, tối đa 12 học sinh mỗi lớp.",
    footerNote: "Nhật ký này là món quà riêng tư dành cho gia đình.",
    indexKicker: "Happy English Club · Hà Nội",
    indexTitle: "Trại Hè 2026",
    indexSub: "Nhật ký riêng về hành trình của mỗi trại sinh — dự án, bước tiến, và những khoảnh khắc làm nên mùa hè ý nghĩa.",
    open: "Xem nhật ký",
  },
};

export function currentLang() {
  return localStorage.getItem("hec-lang") ||
    (navigator.language?.startsWith("vi") ? "vi" : "en");
}

export function setLang(lang) {
  localStorage.setItem("hec-lang", lang);
}

export function applyStrings(lang) {
  const strings = UI_STRINGS[lang];
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (strings[key]) el.textContent = strings[key];
  });
  const toggle = document.getElementById("langToggle");
  if (toggle) toggle.textContent = lang === "en" ? "VI" : "EN";
  document.documentElement.lang = lang;
}

export function initLangToggle(onChange) {
  const toggle = document.getElementById("langToggle");
  if (!toggle) return;
  toggle.addEventListener("click", () => {
    const next = currentLang() === "en" ? "vi" : "en";
    setLang(next);
    applyStrings(next);
    onChange?.(next);
  });
}

let observer;
export function watchReveals(root = document) {
  observer ??= new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          e.target.classList.add("is-visible");
          observer.unobserve(e.target);
        }
      }
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
  );
  root.querySelectorAll(".reveal:not(.is-visible)").forEach((el) => observer.observe(el));
}

/** Dark topbar text over hero; ink once scrolled past it. */
export function initTopbarTint() {
  const topbar = document.getElementById("topbar");
  const brand = document.getElementById("brand");
  const toggle = document.getElementById("langToggle");
  const hero = document.getElementById("hero");
  if (!topbar || !hero) return;
  new IntersectionObserver(
    ([e]) => {
      const overHero = e.isIntersecting;
      topbar.classList.toggle("backdrop-blur-md", !overHero);
      topbar.classList.toggle("bg-ivory/85", !overHero);
      for (const el of [brand, toggle]) {
        if (!el) continue;
        el.classList.toggle("text-white", overHero);
        el.classList.toggle("!text-ink", !overHero);
        if (el === toggle) {
          el.classList.toggle("border-white/40", overHero);
          el.classList.toggle("!border-ink/30", !overHero);
        }
      }
    },
    { rootMargin: "-64px 0px 0px 0px" },
  ).observe(hero);
}
