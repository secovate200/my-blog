function cookie(name) {
  return document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1];
}

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || "연구 데이터를 처리하지 못했습니다.");
    error.status = response.status;
    throw error;
  }
  return data;
}

async function csrfToken() {
  await parseResponse(await fetch("/blog/auth/csrf/", { credentials: "same-origin" }));
  return decodeURIComponent(cookie("csrftoken") ?? "");
}

export async function fetchAdminProjects() {
  return parseResponse(await fetch("/blog/dashboard/projects/", { credentials: "same-origin" }));
}

export async function fetchAdminResearchPosts(project) {
  return parseResponse(await fetch(`/blog/dashboard/projects/${encodeURIComponent(project)}/posts/`, { credentials: "same-origin" }));
}

export async function fetchAdminResearchPost(id) {
  return parseResponse(await fetch(`/blog/dashboard/research-posts/${encodeURIComponent(id)}/`, { credentials: "same-origin" }));
}

async function writeResearchPost(url, method, data) {
  const token = await csrfToken();
  return parseResponse(await fetch(url, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: JSON.stringify(data),
  }));
}

export function createResearchPost(data) {
  return writeResearchPost(`/blog/dashboard/projects/${encodeURIComponent(data.project)}/posts/`, "POST", data);
}

export function updateResearchPost(id, data) {
  return writeResearchPost(`/blog/dashboard/research-posts/${encodeURIComponent(id)}/`, "PUT", data);
}

