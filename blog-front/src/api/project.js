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
