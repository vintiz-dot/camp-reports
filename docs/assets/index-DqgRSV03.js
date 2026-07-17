import{c as r,a as s,i as c,g as l,m as o,U as u,w as m}from"./shared-B1v5r6dp.js";async function p(){const a=r();s(a),c(t=>{s(t),i(t)});let n;try{n=await l()}catch{document.getElementById("studentGrid").innerHTML="<p class='text-ink-soft'>Journals are being prepared…</p>";return}window.__students=n.students,i(a)}function i(a){const n=document.getElementById("studentGrid");n.innerHTML="",(window.__students||[]).forEach((t,d)=>{const e=document.createElement("a");e.className="student-card reveal",e.style.transitionDelay=`${d%3*80}ms`,e.href=`./student.html?s=${encodeURIComponent(t.slug)}`,e.innerHTML=`
      <img loading="lazy" decoding="async" alt="" />
      <div class="veil"></div>
      <div class="absolute bottom-0 inset-x-0 p-6 text-white">
        <p class="font-display text-2xl"></p>
        <p class="text-[0.65rem] tracking-[0.25em] uppercase opacity-80 mt-1"></p>
      </div>`,e.querySelector("img").src=o(t.thumb),e.querySelector(".font-display").textContent=t.name,e.querySelector("p:last-child").textContent=`${t.class?t.class+" · ":""}${u[a].open}`,n.appendChild(e)}),m()}p();
