function cookie(name) {
  return document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1];
}

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || "게시글 요청을 처리하지 못했습니다.");
    error.status = response.status;
    throw error;
  }
  return data;
}

async function csrfToken() {
  await parseResponse(await fetch("/blog/auth/csrf/", { credentials: "same-origin" }));
  return decodeURIComponent(cookie("csrftoken") ?? "");
}

export async function fetchAdminPosts(query = "") {
  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  const search = params.size ? `?${params.toString()}` : "";
  return parseResponse(await fetch(`/blog/dashboard/posts/${search}`, { credentials: "same-origin" }));
}

export async function fetchAdminPost(id) {
  return parseResponse(await fetch(`/blog/dashboard/posts/${encodeURIComponent(id)}/`, { credentials: "same-origin" }));
}

async function writePost(url, method, data) {
  const token = await csrfToken();
  return parseResponse(await fetch(url, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: JSON.stringify(data),
  }));
}

export function createPost(data) {
  return writePost("/blog/dashboard/posts/", "POST", data);
}

export function updatePost(id, data) {
  return writePost(`/blog/dashboard/posts/${encodeURIComponent(id)}/`, "PUT", data);
}

export async function deletePost(id) {
  const token = await csrfToken();
  return parseResponse(await fetch(`/blog/dashboard/posts/${encodeURIComponent(id)}/`, {
    method: "DELETE",
    credentials: "same-origin",
    headers: { "X-CSRFToken": token },
  }));
}

