import apiClient from "./client";

export async function getPosts() {
  // post 조회
  const response = await apiClient.get("/posts/");
  return response.data;
}

export async function getPost(postId) {
  // post 출력
  const response = await apiClient.get(`/posts/${postId}/`);
  return response.data;
}
