import { useEffect, useState } from "react";
import Home from "./Container/Home";
import Category from "./Container/Category";
import Project from "./Container/Project";
import Contact from "./Container/Contact";
import PostDetail, {
  PostTableOfContents,
  ProjectPostDetail,
} from "./Container/PostDetail";
import Header from "./Components/Header";
import Hero from "./Components/Hero";
import Navbar from "./Components/Navbar";
import Profile from "./Components/Profile";
import { ClientError, ServerError } from "./Container/Error";
import { Route, Routes, useLocation } from "react-router-dom";
import "./App.css";

const PAGE_PATHS = [
  /^\/$/,
  /^\/(?:category|contact|project)\/?$/,
  /^\/post\/\d+\/?$/,
  /^\/project\/\d+\/post\/\d+\/?$/,
  /^\/error\/\d{3}\/?$/,
];
const THEME_STORAGE_KEY = "blog-theme";

function getStoredTheme() {
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  return storedTheme === "dark" || storedTheme === "light"
    ? storedTheme
    : "light";
}

function App() {
  const [theme, setTheme] = useState(getStoredTheme);
  const [httpError, setHttpError] = useState(null);
  const location = useLocation();
  const postMatch = location.pathname.match(/^\/post\/(\d+)\/?$/);
  const projectPostMatch = location.pathname.match(
    /^\/project\/(\d+)\/post\/(\d+)\/?$/,
  );
  const errorMatch = window.location.pathname.match(/^\/error\/(\d{3})\/?$/);
  const errorStatus = errorMatch ? Number(errorMatch[1]) : null;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    const handleHttpError = (event) => {
      const status = Number(event.detail?.status);
      setHttpError({
        locationKey: location.key,
        status: status >= 400 && status <= 599 ? status : 500,
      });
    };

    window.addEventListener("app:http-error", handleHttpError);
    return () => window.removeEventListener("app:http-error", handleHttpError);
  }, [location.key]);

  const httpErrorStatus =
    httpError?.locationKey === location.key ? httpError.status : null;
  const isKnownPath = PAGE_PATHS.some((path) => path.test(location.pathname));

  const toggleTheme = () => {
    setTheme((currentTheme) => (currentTheme === "light" ? "dark" : "light"));
  };

  if (errorStatus >= 400 && errorStatus < 500) {
    return <ClientError status={errorStatus} />;
  }

  if (errorStatus >= 500 && errorStatus < 600) {
    return <ServerError status={errorStatus} />;
  }

  if (!isKnownPath) {
    return <ClientError status={404} />;
  }

  if (httpErrorStatus >= 400 && httpErrorStatus < 500) {
    return <ClientError status={httpErrorStatus} />;
  }

  if (httpErrorStatus >= 500 && httpErrorStatus < 600) {
    return <ServerError status={httpErrorStatus} />;
  }

  return (
    <div className="App">
      <Header />
      <Hero />
      <Navbar theme={theme} onThemeToggle={toggleTheme} />
      <div className="container">
        <main className="content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/post/:postId" element={<PostDetail />} />
            <Route path="/category" element={<Category />} />
            <Route path="/project" element={<Project />} />
            <Route
              path="/project/:projectId/post/:postId"
              element={<ProjectPostDetail />}
            />
            <Route path="/contact" element={<Contact />} />
          </Routes>
        </main>
        <aside className="profile">
          {postMatch && <PostTableOfContents postId={postMatch[1]} />}
          {projectPostMatch && (
            <PostTableOfContents
              projectId={projectPostMatch[1]}
              postId={projectPostMatch[2]}
            />
          )}
          <Profile />
        </aside>
      </div>
    </div>
  );
}

export default App;
