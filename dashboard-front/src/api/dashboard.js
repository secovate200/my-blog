export async function fetchAdminCategories() {
  const response = await fetch("/blog/dashboard/categories/", { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || "카테고리를 불러오지 못했습니다.");
    error.status = response.status;
    throw error;
  }
  return data;
}

export async function fetchDashboardSummary() {
  const response = await fetch("/blog/dashboard/summary/", { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || "대시보드 정보를 불러오지 못했습니다.");
    error.status = response.status;
    throw error;
  }
  return data;
}

const cookie = (name) =>
  document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`))
    ?.split("=")[1];

export async function uploadMedia(file) {
  await fetch("/blog/auth/csrf/", { credentials: "same-origin" });
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/blog/assets/upload/", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": decodeURIComponent(cookie("csrftoken") ?? ""),
    },
    body: formData,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.file?.url) {
    const error = new Error(data.message || data.detail || "파일을 업로드하지 못했습니다.");
    error.status = response.status;
    throw error;
  }
  return data.file;
}

