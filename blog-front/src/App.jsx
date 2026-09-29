import { useEffect, useState } from "react";
import Home from "./Container/Home";
import Category from "./Container/Category";
import Project from "./Container/Project";
import Contact from "./Container/Contact";
import Header from "./Components/Header";
import Hero from "./Components/Hero";
import Navbar from "./Components/Navbar";
import Profile from "./Components/Profile";
import { ClientError, ServerError } from "./Container/Error";
import { Route, Routes } from "react-router-dom";
import "./App.css";
function App() {
  const [theme, setTheme] = useState("light");
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
            <Route path="/category" element={<Category />} />
            <Route path="/project" element={<Project />} />
            <Route path="/contact" element={<Contact />} />
          </Routes>
        </main>
        <aside className="profile">
          <Profile />
        </aside>
      </div>
    </div>
  );
}

export default App;
