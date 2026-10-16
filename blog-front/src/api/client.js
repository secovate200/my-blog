/** 공개 API의 기준 주소와 공통 오류 처리를 담당해 도메인 모듈의 중복을 막습니다. */
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
