const THEME_COOKIE = "secovate-theme";
const THEME_STORAGE_KEY = "secovate-theme";
const LEGACY_STORAGE_KEYS = ["theme", "blog-theme"];
const THEME_MAX_AGE = 60 * 60 * 24 * 365;

const isTheme = (value) => value === "light" || value === "dark";

const readCookie = () =>
  document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${THEME_COOKIE}=`))
    ?.split("=")[1];

export const getInitialTheme = () => {
  const sharedTheme = readCookie();
  if (isTheme(sharedTheme)) return sharedTheme;

  const currentTheme = localStorage.getItem(THEME_STORAGE_KEY);
  if (isTheme(currentTheme)) return currentTheme;

  for (const key of LEGACY_STORAGE_KEYS) {
    const legacyTheme = localStorage.getItem(key);
    if (isTheme(legacyTheme)) return legacyTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

export const saveTheme = (theme) => {
  if (!isTheme(theme)) return;
  document.cookie = `${THEME_COOKIE}=${theme}; Path=/; Max-Age=${THEME_MAX_AGE}; SameSite=Lax`;
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  LEGACY_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));
};

export const getSharedTheme = readCookie;
