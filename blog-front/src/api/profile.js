/** 공개 블로그 프로필 설정을 조회합니다. */
import apiClient from "./client";

export async function getSiteProfile() {
  const response = await apiClient.get("/profile/");
  return response.data;
}
