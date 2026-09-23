import React from "react";
import "./style.css";
import { BiSearch } from "react-icons/bi";
function Navbar(props) {
  return (
    <div className="navbar">
      <ul className="navbarMenu">
        <li>
          <a href="#">Home</a>
        </li>
        <li>
          <a href="#">Category</a>
        </li>
        <li>
          <a href="#">Project</a>
        </li>
      </ul>
      <div className="search">
        <input type="text" placeholder="Search.." />
        <button>
          <BiSearch />
        </button>
      </div>
    </div>
  );
}
export default Navbar;
