/** 공개 프로젝트와 프로젝트 글 조회 API를 캡슐화합니다. */
import apiClient from "./client";

export async function getProjects() {
  const response = await apiClient.get("/projects/");
  return response.data;
}

export async function getProject(projectId) {
  const response = await apiClient.get(`/projects/${projectId}/`);
  return response.data;
}

export async function getProjectPost(projectId, postId) {
  const response = await apiClient.get(
    `/projects/${projectId}/posts/${postId}/`,
  );
  return response.data;
}
