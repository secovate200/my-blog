import apiClient from "./client";

export async function createContactMessage(message) {
  const response = await apiClient.post("/contact/", message);
  return response.data;
}
