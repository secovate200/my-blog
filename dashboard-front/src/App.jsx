import { lazy, Suspense, useEffect, useState } from "react";
import { Sidebar } from "./components/Layout/Sidebar";
import { Profile } from "./components/Layout/Profile";
import { Content } from "./Container/Dashboard";
import { BlogContent } from "./Container/Blog";
import { SettingsContent } from "./Container/Settings";
import { CategoriesContent } from "./Container/Categories";
import { ResearchContent } from "./Container/Research";
import { LoginContent, SignupContent } from "./Container/Login";
import "./App.css";
import "./styles/Responsive.css";
import { StatusPage } from "./components/Feedback/StatusPage";
import { getInitialTheme, getSharedTheme, saveTheme } from "./utils/theme";
import { navigateToErrorPage } from "./utils/errorNavigation";
import { fetchAdminCategories, fetchAdminProjects, getCurrentUser, login, logout, signup } from "./api";

const WriteContent = lazy(() =>
  import("./components/Editor/WriteContent").then((module) => ({
    default: module.WriteContent,
  })),
);

const ResearchDetailContent = lazy(() =>
  import("./Container/Research/Detail").then((module) => ({
    default: module.ResearchDetailContent,
  })),
);

const BlogPostContent = lazy(() =>
  import("./Container/Blog/Detail").then((module) => ({ default: module.BlogPostContent })),
);

const PageLoading = () => (
  <main className="content" aria-busy="true" aria-live="polite">
    <div className="page-loading">화면을 불러오는 중...</div>
  </main>
);
export const App = () => {
  const [theme, setTheme] = useState(getInitialTheme);
  const [routeHash, setRouteHash] = useState(() => window.location.hash);
  const page = routeHash.replace("#/", "").split("?")[0] || "dashboard";
  const [user, setUser] = useState(undefined);
  const [categories, setCategories] = useState([]);
  const [researchCategories, setResearchCategories] = useState([]);

  useEffect(() => {
    getCurrentUser().then(setUser).catch((error) => {
      setUser(null);
      navigateToErrorPage(error);
    });
  }, []);

  useEffect(() => {
    const syncSession = async () => {
      if (document.visibilityState === "hidden") return;

      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        if (!currentUser) window.location.hash = "/login";
      } catch (error) {
        navigateToErrorPage(error);
      }
    };

    window.addEventListener("focus", syncSession);
    document.addEventListener("visibilitychange", syncSession);
    return () => {
      window.removeEventListener("focus", syncSession);
      document.removeEventListener("visibilitychange", syncSession);
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    fetchAdminCategories().then(({ items }) => setCategories(items)).catch(() => setCategories([]));
    fetchAdminProjects().then(({ items }) => setResearchCategories(items)).catch(() => setResearchCategories([]));
  }, [user]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    const syncTheme = () => {
      const sharedTheme = getSharedTheme();
      if (sharedTheme === "light" || sharedTheme === "dark") {
        setTheme(sharedTheme);
      }
    };

    window.addEventListener("focus", syncTheme);
    window.addEventListener("storage", syncTheme);
    document.addEventListener("visibilitychange", syncTheme);
    const intervalId = window.setInterval(syncTheme, 1000);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener("focus", syncTheme);
      window.removeEventListener("storage", syncTheme);
      document.removeEventListener("visibilitychange", syncTheme);
    };
  }, []);

  useEffect(() => {
    const handleHashChange = () => setRouteHash(window.location.hash);
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const toggleTheme = () => setTheme((current) => current === "light" ? "dark" : "light");
  const routeParams = new URLSearchParams(routeHash.split("?")[1] || "");
  const researchCategoryId = routeParams.get("category") || "";
  const researchPostId = routeParams.get("id") || "";
  const blogPostId = routeParams.get("id") || "";
  const dashboardSearchQuery = routeParams.get("q") || "";
  const statusCode = ["401", "403", "429", "500"].includes(page)
    ? Number(page)
    : null;

  const handleLogin = async (credentials) => {
    const currentUser = await login(credentials);
    setUser(currentUser);
    window.location.hash = "/dashboard";
  };

  const handleLogout = async () => {
    try {
      await logout();
      setUser(null);
      window.location.hash = "/login";
    } catch (error) {
      navigateToErrorPage(error);
    }
  };

  const handleSignup = (account) => signup(account);

  if (user === undefined) return <PageLoading />;

  if (statusCode) return <StatusPage code={statusCode} />;

  if (!user && page !== "login" && page !== "signup") {
    window.location.hash = "/login";
    return <LoginContent theme={theme} onToggleTheme={toggleTheme} onLogin={handleLogin} />;
  }

  if (page === "login") {
    if (user) window.location.hash = "/dashboard";
    return <LoginContent theme={theme} onToggleTheme={toggleTheme} onLogin={handleLogin} />;
  }

  if (page === "signup") {
    if (user) window.location.hash = "/dashboard";
    return <SignupContent theme={theme} onToggleTheme={toggleTheme} onSignup={handleSignup} />;
  }

  const knownPages = ["dashboard", "blog", "blog-view", "blog-edit", "write", "research", "research-write", "research-view", "research-edit", "settings", "categories"];

  if (!knownPages.includes(page)) {
    return <StatusPage code={404} />;
  }

  const requiredPermission = {
    blog: "viewPosts", "blog-view": "viewPosts", "blog-edit": "changePosts", write: "addPosts",
    research: "viewProjects", "research-view": "viewResearchPosts", "research-write": "addResearchPosts", "research-edit": "changeResearchPosts",
    categories: "viewCategories",
  }[page];
  if (requiredPermission && !user.permissions?.[requiredPermission]) return <StatusPage code={403} />;

  return (
    <div className="dashboard">
      <Sidebar permissions={user.permissions} currentPage={["write", "blog-view", "blog-edit"].includes(page) ? "blog" : ["research-write", "research-view", "research-edit"].includes(page) ? "research" : page === "categories" ? "dashboard" : page} />
      <div className="dashboard--content">
        <Suspense fallback={<PageLoading />}>
          {page === "blog" ? (
            <BlogContent theme={theme} onToggleTheme={toggleTheme} searchQuery={dashboardSearchQuery} />
          ) : page === "blog-view" || page === "blog-edit" ? (
            <BlogPostContent postId={blogPostId} mode={page === "blog-edit" ? "edit" : "view"} theme={theme} categories={categories} permissions={user.permissions} />
          ) : page === "write" ? (
            <WriteContent theme={theme} categoryOptions={categories} />
          ) : page === "research" ? (
            <ResearchContent
              categories={researchCategories}
              onWrite={(categoryId) => { window.location.hash = `/research-write?category=${encodeURIComponent(categoryId)}`; }}
            />
          ) : page === "research-write" ? (
            <WriteContent
              theme={theme}
              categoryOptions={researchCategories}
              initialCategory={researchCategoryId}
              defaultVisibility="private"
              titlePlaceholder="연구 게시글 제목"
              postType="research"
            />
          ) : page === "research-view" || page === "research-edit" ? (
            <ResearchDetailContent postId={researchPostId} mode={page === "research-edit" ? "edit" : "view"} theme={theme} categories={researchCategories} />
          ) : page === "settings" ? (
            <SettingsContent theme={theme} onToggleTheme={toggleTheme} user={user} />
          ) : page === "categories" ? (
            <CategoriesContent showDrafts={Boolean(user.permissions?.viewDraftPosts)} />
          ) : (
            <Content
              theme={theme}
              onToggleTheme={toggleTheme}
              onViewAll={() => { window.location.hash = "/blog"; }}
              onViewCategories={() => { window.location.hash = "/categories"; }}
              onViewPosts={() => { window.location.hash = "/blog"; }}
              onViewResearch={() => { window.location.hash = "/research"; }}
            />
          )}
        </Suspense>
        <Profile
          name={user?.name ?? "Secovate"}
          role={user?.role ?? "관리자"}
          theme={theme}
          onToggleTheme={toggleTheme}
          onWritePost={() => { window.location.hash = "/write"; }}
          onMyPage={() => { window.location.hash = "/settings"; }}
          onLogout={handleLogout}
          onSearch={(query) => { window.location.hash = query ? `/blog?q=${encodeURIComponent(query)}` : "/blog"; }}
          searchQuery={page === "blog" ? dashboardSearchQuery : ""}
          canAccessAdmin={Boolean(user?.is_staff)}
          canWritePost={Boolean(user.permissions?.addPosts)}
        />
      </div>
    </div>
  );
};
