function cookie(name) {
  return document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1];
}

async function responseJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || "요청을 처리하지 못했습니다.");
    error.status = response.status;
    throw error;
  }
  return data;
}

async function ensureCsrf() {
  await responseJson(await fetch("/blog/auth/csrf/", { credentials: "same-origin" }));
  return decodeURIComponent(cookie("csrftoken") ?? "");
}

export async function getCurrentUser() {
  const response = await fetch("/blog/auth/me/", { credentials: "same-origin" });
  if (response.status === 401 || response.status === 403) return null;
  return responseJson(response);
}

export async function login({ account, password }) {
  const csrfToken = await ensureCsrf();
  return responseJson(await fetch("/blog/auth/login/", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify({ account, password }),
  }));
}

export async function signup({ name, email, password }) {
  const csrfToken = await ensureCsrf();
  return responseJson(await fetch("/blog/auth/signup/", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify({ name, email, password }),
  }));
}

export async function logout() {
  const csrfToken = await ensureCsrf();
  return responseJson(await fetch("/blog/auth/logout/", {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": csrfToken },
  }));
}

export async function changePassword({ currentPassword, newPassword, newPasswordConfirm }) {
  const csrfToken = await ensureCsrf();
  return responseJson(await fetch("/blog/auth/password/", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    }),
  }));
}
