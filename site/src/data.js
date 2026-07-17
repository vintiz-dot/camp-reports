/**
 * Data layer. Today: static JSON on GitHub Pages.
 * Tomorrow: swap the internals for Supabase without touching the UI —
 *   e.g. supabase.from("students").select("*").eq("slug", slug).single()
 */

const BASE = import.meta.env.BASE_URL;

export async function getStudentIndex() {
  const res = await fetch(`${BASE}data/students.json`);
  if (!res.ok) throw new Error(`students.json ${res.status}`);
  return res.json();
}

export async function getStudent(slug) {
  if (!/^[a-z0-9-]+$/.test(slug)) throw new Error("bad slug");
  const res = await fetch(`${BASE}data/students/${slug}.json`);
  if (!res.ok) throw new Error(`student ${slug} ${res.status}`);
  return res.json();
}

export function mediaUrl(path) {
  return `${BASE}${path}`;
}
