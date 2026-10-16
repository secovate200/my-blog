/** 대시보드 요약 조회와 에디터 파일 업로드 API를 제공합니다. */
import { apiRequest } from "./client";

export async function fetchAdminCategories() {
  return apiRequest("/blog/dashboard/categories/", { fallbackMessage: "카테고리를 불러오지 못했습니다." });
}

export async function fetchDashboardSummary() {
  return apiRequest("/blog/dashboard/summary/", { fallbackMessage: "대시보드 정보를 불러오지 못했습니다." });
}

export async function uploadMedia(file) {
  const formData = new FormData();
  formData.append("file", file);
  const data = await apiRequest("/blog/assets/upload/", {
    method: "POST",
    body: formData,
    requiresCsrf: true,
    fallbackMessage: "파일을 업로드하지 못했습니다.",
  });
  if (!data.file?.url) throw new Error("서버가 업로드된 파일 주소를 반환하지 않았습니다.");
  return data.file;
}

