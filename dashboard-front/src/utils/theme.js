const THEME_COOKIE = "secovate-theme";
const THEME_MAX_AGE = 60 * 60 * 24 * 365;

const readCookie = () =>
  document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${THEME_COOKIE}=`))
    ?.split("=")[1];

export const getInitialTheme = () => {
  const sharedTheme = readCookie();
  if (sharedTheme === "light" || sharedTheme === "dark") return sharedTheme;

  const previousTheme = localStorage.getItem("theme");
  if (previousTheme === "light" || previousTheme === "dark") return previousTheme;

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

export const saveTheme = (theme) => {
  document.cookie = `${THEME_COOKIE}=${theme}; Path=/; Max-Age=${THEME_MAX_AGE}; SameSite=Lax`;
  localStorage.setItem("theme", theme);
};

export const getSharedTheme = readCookie;
