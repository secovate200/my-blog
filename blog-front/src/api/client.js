import axios from "axios";

const apiClient = axios.create({
  baseURL: "/blog",
  timeout: 5000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isReadRequest = error.config?.method?.toLowerCase() === "get";

    if (isReadRequest && !axios.isCancel(error)) {
      const status =
        error.response?.status ?? (error.code === "ECONNABORTED" ? 504 : 503);
      window.dispatchEvent(
        new CustomEvent("app:http-error", { detail: { status } }),
      );
    }

    return Promise.reject(error);
  },
);

export default apiClient;
