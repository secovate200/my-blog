const errorStatusPages = new Set([401, 403, 404, 429, 500]);

export function getErrorStatus(error, fallback = 500) {
  const status = Number(error?.status);

  if (errorStatusPages.has(status)) return status;
  if (status >= 500) return 500;
  return fallback;
}

export function navigateToErrorPage(error, fallback = 500) {
  window.location.hash = `/${getErrorStatus(error, fallback)}`;
}
