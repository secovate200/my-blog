/**
 * 대시보드 API의 공통 요청 흐름을 담당합니다.
 *
 * 쿠키 해석, CSRF 토큰 준비, 오류 변환을 한곳에 모아 각 도메인 API가
 * URL과 데이터 형태에만 집중하도록 합니다. 이 계층을 통하면 서버 오류가
 * 항상 status를 가진 Error로 변환되어 화면의 오류 처리 방식도 일관됩니다.
 */

const CSRF_COOKIE_NAME = "csrftoken";
const CSRF_ENDPOINT = "/blog/auth/csrf/";
const DEFAULT_ERROR_MESSAGE = "요청을 처리하지 못했습니다.";

function readCookie(name) {
  const encodedValue = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`))
    ?.split("=")[1];

  return decodeURIComponent(encodedValue ?? "");
}

async function parseResponse(response, fallbackMessage = DEFAULT_ERROR_MESSAGE) {
  // 오류 응답이 HTML이거나 본문이 비어 있어도 원래 HTTP 상태를 보존해야
  // 화면이 401, 403, 500 등의 알맞은 오류 페이지로 이동할 수 있습니다.
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || data.message || fallbackMessage);
    error.status = response.status;
    throw error;
  }

  return data;
}

async function getCsrfToken() {
  const response = await fetch(CSRF_ENDPOINT, { credentials: "same-origin" });
  await parseResponse(response, "보안 토큰을 준비하지 못했습니다.");
  return readCookie(CSRF_COOKIE_NAME);
}

export async function apiRequest(
  url,
  {
    method = "GET",
    data,
    body,
    headers = {},
    requiresCsrf = false,
    fallbackMessage = DEFAULT_ERROR_MESSAGE,
  } = {},
) {
  const requestHeaders = { ...headers };

  if (requiresCsrf) {
    requestHeaders["X-CSRFToken"] = await getCsrfToken();
  }

  if (data !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
  }

  const response = await fetch(url, {
    method,
    credentials: "same-origin",
    headers: requestHeaders,
    body: data === undefined ? body : JSON.stringify(data),
  });

  return parseResponse(response, fallbackMessage);
}

