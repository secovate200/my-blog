const THEME_COOKIE = "secovate-theme";
const THEME_STORAGE_KEY = "secovate-theme";
const LEGACY_STORAGE_KEYS = ["blog-theme", "theme"];
const THEME_MAX_AGE = 60 * 60 * 24 * 365;

const isTheme = (value) => value === "light" || value === "dark";

const readCookie = () => {
  const value = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${THEME_COOKIE}=`))
    ?.split("=")[1];
  return isTheme(value) ? value : null;
};

const readStoredTheme = () => {
  const current = localStorage.getItem(THEME_STORAGE_KEY);
  if (isTheme(current)) return current;

  for (const key of LEGACY_STORAGE_KEYS) {
    const legacy = localStorage.getItem(key);
    if (isTheme(legacy)) return legacy;
  }
  return null;
};

export const getInitialTheme = () =>
  readCookie()
  ?? readStoredTheme()
  ?? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

export const saveTheme = (theme) => {
  if (!isTheme(theme)) return;
  document.cookie = `${THEME_COOKIE}=${theme}; Path=/; Max-Age=${THEME_MAX_AGE}; SameSite=Lax`;
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  LEGACY_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));
};

export const getSharedTheme = readCookie;
