import { useEffect, useState } from "react";
import Home from "./Container/Home";
import Category from "./Container/Category";
import Project from "./Container/Project";
import Contact from "./Container/Contact";
import PostDetail, { PostTableOfContents } from "./Container/PostDetail";
import Header from "./Components/Header";
import Hero from "./Components/Hero";
import Navbar from "./Components/Navbar";
import Profile from "./Components/Profile";
import { ClientError, ServerError } from "./Container/Error";
import { Route, Routes, useLocation } from "react-router-dom";
import "./App.css";
function App() {
  const [theme, setTheme] = useState("light");
  const location = useLocation();
  const postMatch = location.pathname.match(/^\/post\/(\d+)\/?$/);
  const errorMatch = window.location.pathname.match(/^\/error\/(\d{3})\/?$/);
  const errorStatus = errorMatch ? Number(errorMatch[1]) : null;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const toggleTheme = () => {
    setTheme((currentTheme) => (currentTheme === "light" ? "dark" : "light"));
  };

  if (errorStatus >= 400 && errorStatus < 500) {
    return <ClientError status={errorStatus} />;
  }

  if (errorStatus >= 500 && errorStatus < 600) {
    return <ServerError status={errorStatus} />;
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
            <Route path="/contact" element={<Contact />} />
          </Routes>
        </main>
        <aside className="profile">
          {postMatch && <PostTableOfContents postId={postMatch[1]} />}
          <Profile />
        </aside>
      </div>
    </div>
  );
}

export default App;
