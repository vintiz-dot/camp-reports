/**
 * Marketing landing page. Vietnamese-first (target: Hanoi parents),
 * EN toggle shares the same localStorage key as the journals.
 * Every number and quote here comes from real camp data — nothing invented.
 */
import { watchReveals } from "./shared.js";

const L = {
  vi: {
    ctaShort: "Học thử miễn phí",
    heroKicker: "Trại Hè HEC · Đống Đa, Hà Nội",
    heroTitle: "Mùa hè này, con không chỉ học tiếng Anh. Con sống trong tiếng Anh.",
    heroSub: "Trại hè toàn tiếng Anh với giáo viên Mỹ có bằng sư phạm, giáo trình Oxford & Cambridge, và lớp học không quá 12 học sinh — nơi mỗi đứa trẻ đều được nhìn thấy.",
    ctaPrimary: "Đăng ký học thử miễn phí",
    ctaSecondary: "Xem hành trình của các con",
    ctaSite: "Về trang chủ HEC",
    chips: ["Giáo viên tốt nghiệp tại Mỹ có bằng sư phạm", "Giáo trình Oxford & Cambridge", "Tối đa 12 học sinh / lớp"],
    proof: [
      ["19", "học viên mùa hè 2026"],
      ["40", "Ngày được ghi lại tại trại hè"],
      ["1.400+", "khoảnh khắc ảnh & video"],
      ["9", "video các con tự kể"],
    ],
    journeyKicker: "Hành trình mùa hè 2026",
    journeyTitle: "Từ buổi sáng đầu tiên bỡ ngỡ đến ngày cuối đầy tự hào.",
    journey: [
      { img: "media/landing/journey-1.jpg", t: "Ngày đầu bỡ ngỡ", b: "Nhiều con bước vào lớp mà chưa dám giơ tay. Trong một lớp học nhỏ, sự rụt rè không bị bỏ quên — nó được nhẹ nhàng mời ra ánh sáng." },
      { img: "media/landing/journey-2.jpg", t: "Dự án & đôi tay", b: "Các con học qua trải nghiệm thực tế: tự tay xây dựng mô hình, thiết kế áp phích và tự tin thuyết trình. Khi kiến thức đi qua đôi tay, kiến thức sẽ ở lại lâu hơn trong tâm trí." },
      { img: "media/landing/journey-3.jpg", t: "Dám nói, dám sai", b: "Cả ngày trong môi trường tiếng Anh, các con học được điều quý nhất: nói ra suy nghĩ của mình mà không sợ sai." },
      { img: "media/landing/journey-4.jpg", t: "Ngày cuối tự hào", b: "Đứng trước lớp, trình bày sản phẩm của chính mình — sự tự tin ấy không thể dạy qua sách vở. Nó phải được sống qua." },
    ],
    videoKicker: "Con tự kể",
    videoTitle: "Không kịch bản. Không đạo diễn. Chỉ có lời của các con.",
    videoSub: "Cuối trại, chúng tôi ngồi xuống cùng từng con và hỏi về hành trình của mình — từ ngày đầu đến ngày cuối. Đây là câu trả lời của các con.",
    quotesKicker: "Thầy cô nhìn thấy từng con",
    quotesTitle: "Mỗi học viên đều nhận được nhận xét chuyên môn — viết riêng cho mình.",
    quotes: [
      { q: "Việc hòa mình vào môi trường giao tiếp chủ yếu bằng tiếng Anh đã mở khóa một điều kỳ diệu: giờ đây con tự ghép câu và diễn đạt rõ ràng điều mình muốn.", n: "Nhận xét dành cho Ronaldo — học viên tiến bộ nhất" },
      { q: "Dù khó đến đâu, thách thức đến đâu, con luôn là người đầu tiên hỏi: “Thầy ơi, con làm cái này được không?” Với con, không gì là không thể.", n: "Nhận xét dành cho Pizza" },
      { q: "Mỗi khi hoàn thành bài tập trên lớp, con — không cần ai nhắc — lấy bài tập về nhà ra và bắt đầu làm ngay tại trại.", n: "Nhận xét dành cho Elina — học viên nhỏ tuổi nhất" },
    ],
    journalKicker: "Món quà cuối trại hè",
    journalTitle: "Mỗi con tốt nghiệp với một cuốn nhật ký số của riêng mình.",
    journalBody: "Không phải giấy khen in sẵn. Mỗi gia đình có con theo học tại HEC sẽ nhận một trang nhật ký riêng cho con: video nổi bật, bộ ảnh được chọn lọc qua cả mùa hè, video con tự kể về hành trình, và nhận xét song ngữ do giáo viên viết riêng — theo tinh thần đánh giá của các trường quốc tế.",
    journalCta: "Xem nhật ký của các con",
    whyKicker: "Vì sao phụ huynh chọn HEC",
    whyTitle: "Chất lượng có thể kiểm chứng — không phải lời hứa.",
    why: [
      { t: "Giáo viên tốt nghiệp tại Mỹ", b: "Con học phát âm, tư duy và văn hóa từ một nhà giáo dục thực thụ — kỹ sư chuyển ngành sư phạm, tận tâm với từng học sinh." },
      { t: "Giáo trình Oxford & Cambridge", b: "Chuẩn quốc tế đã được kiểm chứng, điều chỉnh phù hợp với trẻ em Việt Nam." },
      { t: "Tối đa 12 học sinh mỗi lớp", b: "Trong lớp học nhỏ, không con nào vô hình. Thầy cô biết từng điểm mạnh, từng bước tiến của mỗi con — và chứng minh điều đó trong nhật ký cuối trại." },
      { t: "Học phí minh bạch 210.000₫/buổi", b: "Biết trước từng đồng, không gói hàng chục triệu đồng mập mờ. Kèm Câu lạc bộ Đọc sách thứ Bảy hoàn toàn miễn phí." },
    ],
    finalKicker: "Trại hè tiếp theo",
    finalTitle: "Mỗi lớp chỉ có 12 chỗ. Mùa hè của con chỉ có một.",
    finalSub: "Đăng ký học thử miễn phí để gặp thầy, thăm lớp, và để con tự cảm nhận. Không cam kết, không áp lực — chỉ một buổi học thật.",
    finalNote: "HEC · Đống Đa, Hà Nội · Nhắn tin cho chúng tôi qua hanoienglish.vip",
    footerTag: "Lớp học nhỏ, tự tin lớn. Giáo viên Mỹ có bằng sư phạm, giáo trình Oxford & Cambridge, tối đa 12 học sinh mỗi lớp.",
  },
  en: {
    ctaShort: "Free trial class",
    heroKicker: "HEC Summer Camp · Đống Đa, Hanoi",
    heroTitle: "This summer, your child doesn't just study English. They live in it.",
    heroSub: "An all-English summer camp with a US-licensed teacher, Oxford & Cambridge curriculum, and classes capped at 12 — where every child is truly seen.",
    ctaPrimary: "Book a free trial class",
    ctaSecondary: "See the campers' journey",
    ctaSite: "Visit HEC's homepage",
    chips: ["US-licensed teacher", "Oxford & Cambridge curriculum", "Max 12 students per class"],
    proof: [
      ["19", "campers in summer 2026"],
      ["40", "camp days documented"],
      ["1,400+", "photo & video moments"],
      ["9", "student reflection videos"],
    ],
    journeyKicker: "The Summer 2026 journey",
    journeyTitle: "From a nervous first morning to a proud final day.",
    journey: [
      { img: "media/landing/journey-1.jpg", t: "The nervous first day", b: "Many children walk in not yet daring to raise a hand. In a small class, shyness is never overlooked — it is gently invited into the light." },
      { img: "media/landing/journey-2.jpg", t: "Projects & busy hands", b: "Campers learn by making: building models, designing posters, presenting their work. Knowledge that passes through the hands stays in the mind." },
      { img: "media/landing/journey-3.jpg", t: "Daring to speak, daring to be wrong", b: "Immersed in English all day, children learn the most valuable thing of all: to say what they think without fearing mistakes." },
      { img: "media/landing/journey-4.jpg", t: "The proud last day", b: "Standing before the class, presenting work that is truly theirs — that confidence cannot be taught from a book. It has to be lived." },
    ],
    videoKicker: "In their own words",
    videoTitle: "No script. No directing. Just the campers' own voices.",
    videoSub: "At the end of camp we sat down with each child and asked about their journey — from day one to the last day. These are their answers.",
    quotesKicker: "A teacher who sees every child",
    quotesTitle: "Every camper receives a professional reflection — written just for them.",
    quotes: [
      { q: "Immersing him in an environment that asked him to communicate mainly in English unlocked something remarkable: he now puts sentences together and clearly articulates what he wants.", n: "From Ronaldo's reflection — most improved camper" },
      { q: "No matter how difficult, how challenging, or how outright absurd a build appears, he is always the first to ask: “Teacher, can I build this one?” To him, impossible is nothing.", n: "From Pizza's reflection" },
      { q: "Whenever she finishes her classroom tasks, she takes out her school homework — unasked — and begins working on it right there in camp.", n: "From Elina's reflection — youngest camper" },
    ],
    journalKicker: "The end-of-camp gift",
    journalTitle: "Every camper graduates with a digital journal of their own.",
    journalBody: "Not a printed certificate. Every HEC family receives a private journal page: a highlight film, a photo collection curated across the whole summer, the child's own reflection video, and a bilingual teacher's assessment written individually — in the spirit of international-school reporting.",
    journalCta: "Browse the student journals",
    whyKicker: "Why parents choose HEC",
    whyTitle: "Quality you can verify — not promises.",
    why: [
      { t: "US-licensed teacher", b: "Your child learns pronunciation, thinking, and culture from a real educator — an engineer turned teacher, devoted to every student." },
      { t: "Oxford & Cambridge curriculum", b: "Internationally proven standards, adapted thoughtfully for Vietnamese children." },
      { t: "Max 12 students per class", b: "In a small class no child is invisible. The teacher knows each child's strengths and progress — and proves it in the end-of-camp journal." },
      { t: "Transparent 210,000₫ per session", b: "Every đồng known upfront — no opaque multi-million packages. Plus a completely free Saturday Reading Club." },
    ],
    finalKicker: "The next camp",
    finalTitle: "Only 12 seats per class. Your child's summer happens once.",
    finalSub: "Book a free trial class to meet the teacher, see the classroom, and let your child feel it for themselves. No commitment, no pressure — just one real lesson.",
    finalNote: "HEC · Đống Đa, Hanoi · Message us via hanoienglish.vip",
    footerTag: "Small classes, big confidence. A US-licensed teacher, Oxford & Cambridge curriculum, and no more than 12 students per class.",
  },
};

const VIDEOS = [
  { id: "G3ZjYQe7gEw", name: "Ronaldo" },
  { id: "WIzYsa_DkNk", name: "Jessica" },
  { id: "XLKBOWDRHLA", name: "William" },
];

const JOURNAL_CARDS = [
  { slug: "emma", name: "Emma", img: "media/emma/hero.jpg" },
  { slug: "pizza", name: "Pizza", img: "media/pizza/hero.jpg" },
  { slug: "rainbow", name: "Rainbow", img: "media/rainbow/hero.jpg" },
];

function lang() {
  return localStorage.getItem("hec-lang") || "vi"; // Vietnamese-first by design
}

function render(l) {
  const s = L[l];
  document.documentElement.lang = l;
  document.querySelectorAll("[data-l]").forEach((el) => {
    const v = s[el.dataset.l];
    if (typeof v === "string") el.textContent = v;
  });
  document.getElementById("langToggle").textContent = l === "vi" ? "EN" : "VI";

  const chips = document.getElementById("heroChips");
  chips.innerHTML = "";
  s.chips.forEach((c) => {
    const span = document.createElement("span");
    span.className = "border-l border-(--color-gold-soft) pl-3 first:border-0 first:pl-0";
    span.textContent = c;
    chips.appendChild(span);
  });

  const proof = document.getElementById("proofBand");
  proof.innerHTML = "";
  s.proof.forEach(([v, label]) => {
    const div = document.createElement("div");
    div.className = "reveal";
    div.innerHTML = `<p class="stat-value" data-count="${v}"></p>
      <p class="text-[0.65rem] tracking-[0.22em] uppercase text-ink-soft mt-2"></p>`;
    div.querySelector(".stat-value").textContent = v;
    div.querySelector("p:last-child").textContent = label;
    proof.appendChild(div);
  });

  const steps = document.getElementById("journeySteps");
  steps.innerHTML = "";
  s.journey.forEach((st, i) => {
    const fig = document.createElement("figure");
    fig.className = "reveal";
    fig.style.transitionDelay = `${(i % 2) * 90}ms`;
    fig.innerHTML = `
      <div class="overflow-hidden rounded-sm aspect-[3/2] bg-(--color-ivory-deep)">
        <img loading="lazy" decoding="async" class="w-full h-full object-cover hover:scale-[1.03] transition-transform duration-1000" alt="" />
      </div>
      <figcaption class="mt-6">
        <p class="section-no"></p>
        <h3 class="font-display text-2xl mt-1"></h3>
        <p class="mt-3 text-ink-soft max-w-lg"></p>
      </figcaption>`;
    fig.querySelector("img").src = st.img;
    fig.querySelector(".section-no").textContent = String(i + 1).padStart(2, "0");
    fig.querySelector("h3").textContent = st.t;
    fig.querySelector("figcaption p:last-child").textContent = st.b;
    steps.appendChild(fig);
  });

  const vids = document.getElementById("videoGrid");
  vids.innerHTML = "";
  VIDEOS.forEach((v, i) => {
    const div = document.createElement("div");
    div.className = "reveal";
    div.style.transitionDelay = `${i * 90}ms`;
    div.innerHTML = `
      <div class="aspect-video overflow-hidden rounded-sm bg-black/40">
        <iframe class="w-full h-full" loading="lazy"
          src="https://www.youtube-nocookie.com/embed/${v.id}?rel=0"
          title="${v.name}" allow="accelerometer; encrypted-media; picture-in-picture"
          allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
      </div>
      <p class="mt-3 text-sm text-ivory/70 tracking-[0.15em] uppercase">${v.name}</p>`;
    vids.appendChild(div);
  });

  const quotes = document.getElementById("quoteCards");
  quotes.innerHTML = "";
  s.quotes.forEach((q, i) => {
    const card = document.createElement("blockquote");
    card.className = "strength-card reveal";
    card.style.transitionDelay = `${i * 90}ms`;
    card.innerHTML = `
      <p class="font-display text-4xl text-(--color-gold) leading-none">“</p>
      <p class="font-display text-lg leading-relaxed mt-2"></p>
      <footer class="mt-5 text-[0.7rem] tracking-[0.18em] uppercase text-ink-soft"></footer>`;
    card.querySelector("p:nth-child(2)").textContent = q.q;
    card.querySelector("footer").textContent = q.n;
    quotes.appendChild(card);
  });

  const jc = document.getElementById("journalCards");
  jc.innerHTML = "";
  JOURNAL_CARDS.forEach((c, i) => {
    const a = document.createElement("a");
    a.className = "student-card reveal !aspect-[3/4]";
    a.style.transitionDelay = `${i * 90}ms`;
    a.href = `./student.html?s=${c.slug}`;
    a.innerHTML = `
      <img loading="lazy" decoding="async" alt="" />
      <div class="veil"></div>
      <p class="absolute bottom-3 left-4 text-white font-display text-lg"></p>`;
    a.querySelector("img").src = c.img;
    a.querySelector("p").textContent = c.name;
    jc.appendChild(a);
  });

  const why = document.getElementById("whyCards");
  why.innerHTML = "";
  s.why.forEach((w, i) => {
    const card = document.createElement("article");
    card.className = "strength-card reveal";
    card.style.transitionDelay = `${i * 80}ms`;
    card.innerHTML = `
      <h3 class="font-display text-xl attr"></h3>
      <p class="mt-3 text-sm text-ink-soft leading-relaxed"></p>`;
    card.querySelector("h3").textContent = w.t;
    card.querySelector("p").textContent = w.b;
    why.appendChild(card);
  });

  watchReveals();
}

function initTopbar() {
  const topbar = document.getElementById("topbar");
  const brand = document.getElementById("brand");
  const toggle = document.getElementById("langToggle");
  const hero = document.getElementById("hero");
  new IntersectionObserver(([e]) => {
    const over = e.isIntersecting;
    topbar.classList.toggle("backdrop-blur-md", !over);
    topbar.classList.toggle("bg-ivory/85", !over);
    for (const el of [brand, toggle]) {
      el.classList.toggle("text-white", over);
      el.classList.toggle("!text-ink", !over);
    }
    toggle.classList.toggle("border-white/40", over);
    toggle.classList.toggle("!border-ink/30", !over);
  }, { rootMargin: "-64px 0px 0px 0px" }).observe(hero);
}

render(lang());
initTopbar();
document.getElementById("langToggle").addEventListener("click", () => {
  const next = lang() === "vi" ? "en" : "vi";
  localStorage.setItem("hec-lang", next);
  render(next);
});
