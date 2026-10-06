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

export const uploadMedia = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result);
  reader.onerror = () => reject(reader.error);
  reader.readAsDataURL(file);
});

