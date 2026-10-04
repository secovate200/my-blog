import apiClient from "./client";

export async function getPosts({
  page = 1,
  category = "",
  tag = "",
  query = "",
} = {}) {
  // post 조회
  const response = await apiClient.get("/posts/", {
    params: {
      page,
      ...(category && { category }),
      ...(tag && { tag }),
      ...(query && { q: query }),
    },
  });
  return response.data;
}

export async function getAllPosts() {
  const posts = [];
  let page = 1;
  let hasNextPage = true;

  while (hasNextPage) {
    const data = await getPosts({ page });
    if (Array.isArray(data)) return data;
    posts.push(...(data.results ?? []));
    hasNextPage = Boolean(data.next);
    page += 1;
  }

  return posts;
}

export async function getPost(postId) {
  // post 출력
  const response = await apiClient.get(`/posts/${postId}/`);
  return response.data;
}
