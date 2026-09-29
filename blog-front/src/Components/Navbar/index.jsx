import { useEffect, useRef, useState } from "react";
import "./style.css";
import { BiMoon, BiSearch, BiSun } from "react-icons/bi";
import { Link } from "react-router-dom";

function Navbar({ theme, onThemeToggle }) {
  const navbarRef = useRef(null);
  const [isStuck, setIsStuck] = useState(false);

  useEffect(() => {
    const updateStickyState = () => {
      const navbarTop = navbarRef.current?.getBoundingClientRect().top;
      setIsStuck(window.scrollY > 0 && navbarTop <= 0);
    };

    updateStickyState();
    window.addEventListener("scroll", updateStickyState, { passive: true });
    window.addEventListener("resize", updateStickyState);

    return () => {
      window.removeEventListener("scroll", updateStickyState);
      window.removeEventListener("resize", updateStickyState);
    };
  }, []);

  return (
    <div ref={navbarRef} className={`navbar ${isStuck ? "navbarStuck" : ""}`}>
      <ul className="navbarMenu">
        <li>
          <Link to="/">Home</Link>
        </li>
        <li>
          <Link to="/category">Category</Link>
        </li>
        <li>
          <Link to="/contact">Contact</Link>
        </li>
        <li>
          <Link to="/project">Project</Link>
        </li>
      </ul>
      <div className="search">
        <form action="" method="get" name="search">
          <input type="text" placeholder="Search.." />
          <button>
            <BiSearch />
          </button>
        </form>
        <button
          className="themeToggle"
          type="button"
          onClick={onThemeToggle}
          aria-label={`${theme === "dark" ? "라이트" : "다크"} 모드로 전환`}
          title={`${theme === "dark" ? "라이트" : "다크"} 모드`}
        >
          {theme === "dark" ? <BiSun /> : <BiMoon />}
        </button>
      </div>
    </div>
  );
}
export default Navbar;
