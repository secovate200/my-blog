import "./style.css";
import { BiMoon, BiSearch, BiSun } from "react-icons/bi";
import { Link } from "react-router-dom";

function Navbar({ theme, onThemeToggle }) {
  return (
    <div className="navbar">
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
