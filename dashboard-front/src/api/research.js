/** 프로젝트 연구 글 API를 한곳에서 관리합니다. */
import { apiRequest } from "./client";

const RESEARCH_ERROR_MESSAGE = "연구 데이터를 처리하지 못했습니다.";

export async function fetchAdminProjects() {
  return apiRequest("/blog/dashboard/projects/", { fallbackMessage: RESEARCH_ERROR_MESSAGE });
}

export async function fetchAdminResearchPosts(project) {
  return apiRequest(`/blog/dashboard/projects/${encodeURIComponent(project)}/posts/`, { fallbackMessage: RESEARCH_ERROR_MESSAGE });
}

export async function fetchAdminResearchPost(id) {
  return apiRequest(`/blog/dashboard/research-posts/${encodeURIComponent(id)}/`, { fallbackMessage: RESEARCH_ERROR_MESSAGE });
}

async function writeResearchPost(url, method, data) {
  return apiRequest(url, {
    method,
    data,
    requiresCsrf: true,
    fallbackMessage: RESEARCH_ERROR_MESSAGE,
  });
}

export function createResearchPost(data) {
  return writeResearchPost(`/blog/dashboard/projects/${encodeURIComponent(data.project)}/posts/`, "POST", data);
}

export function updateResearchPost(id, data) {
  return writeResearchPost(`/blog/dashboard/research-posts/${encodeURIComponent(id)}/`, "PUT", data);
}

