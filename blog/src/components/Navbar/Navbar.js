import React from "react";
import "./style.css";
import { FaSearch } from "react-icons/fa";
function Navbar(props) {
  return (
    <div className="navbar">
      <ul className="navbarMenu">
        <li>
          <a href="#">Home</a>
        </li>
        <li>
          <a href="#">Categories</a>
        </li>
        <li>
          <a href="#">Project</a>
        </li>
      </ul>
      <div className="search">
        <input type="text" placeholder="Search..." />
        <FaSearch />
      </div>
    </div>
  );
}
export default Navbar;
