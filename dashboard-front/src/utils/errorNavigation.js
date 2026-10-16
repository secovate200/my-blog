/** API 오류 상태를 지원되는 오류 화면으로 제한해 잘못된 경로 이동을 방지합니다. */
const errorStatusPages = new Set([400, 401, 403, 404, 429, 500]);

export function getErrorStatus(error, fallback = 500) {
  const status = Number(error?.status);

  if (errorStatusPages.has(status)) return status;
  if (status >= 500) return 500;
  return fallback;
}

export function navigateToErrorPage(error, fallback = 500) {
  window.location.hash = `/${getErrorStatus(error, fallback)}`;
}
