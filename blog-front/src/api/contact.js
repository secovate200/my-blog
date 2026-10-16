/** 문의 화면이 HTTP 세부사항을 알지 않도록 전송 API를 제공합니다. */
import apiClient from "./client";

export async function createContactMessage(message) {
  const response = await apiClient.post("/contact/", message);
  return response.data;
}
