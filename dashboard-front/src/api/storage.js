/** 실제 API 전환 전의 로컬 개발 데이터를 안전하게 읽고 저장하는 어댑터입니다. */
export const STORAGE_KEYS = {
  posts: "secovate-demo-posts",
  projects: "secovate-demo-projects",
  research: "secovate-demo-research",
};

export const categories = ["Security", "Development", "Backend", "Writing", "Design", "Database"]
  .map((name, index) => ({ id: index + 1, name }));

export const initialProjects = [
  { id: "web-security", name: "웹 보안 연구", field: "Web Security", status: "in_progress", visibility: "private", postCount: 0 },
  { id: "reverse-engineering", name: "리버스 엔지니어링", field: "Reverse Engineering", status: "research", visibility: "private", postCount: 0 },
  { id: "ideas", name: "연구 아이디어", field: "Ideas", status: "research", visibility: "private", postCount: 0 },
];

export function readStorage(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}

export function saveStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
  return value;
}

export const resolveLater = (value) => new Promise((resolve) => setTimeout(() => resolve(value), 120));

