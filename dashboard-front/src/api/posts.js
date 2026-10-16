/** 게시글 도메인의 조회와 변경 요청을 제공합니다. */
import { apiRequest } from "./client";

const POST_ERROR_MESSAGE = "게시글 요청을 처리하지 못했습니다.";

export async function fetchAdminPosts(query = "") {
  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  const search = params.size ? `?${params.toString()}` : "";
  return apiRequest(`/blog/dashboard/posts/${search}`, { fallbackMessage: POST_ERROR_MESSAGE });
}

export async function fetchAdminPost(id) {
  return apiRequest(`/blog/dashboard/posts/${encodeURIComponent(id)}/`, { fallbackMessage: POST_ERROR_MESSAGE });
}

async function writePost(url, method, data) {
  return apiRequest(url, {
    method,
    data,
    requiresCsrf: true,
    fallbackMessage: POST_ERROR_MESSAGE,
  });
}

export function createPost(data) {
  return writePost("/blog/dashboard/posts/", "POST", data);
}

export function updatePost(id, data) {
  return writePost(`/blog/dashboard/posts/${encodeURIComponent(id)}/`, "PUT", data);
}

export async function deletePost(id) {
  return apiRequest(`/blog/dashboard/posts/${encodeURIComponent(id)}/`, {
    method: "DELETE",
    requiresCsrf: true,
    fallbackMessage: POST_ERROR_MESSAGE,
  });
}

