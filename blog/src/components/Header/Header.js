import React from "react";
import "./style.css";
function Header(props) {
  return (
    <header className="header">
      <nav className="headerMenu">
        <a href="#">Home</a>
        <a href="#">Login</a>
        <a href="#">Logout</a>
        <a href="#">Dashboard</a>
      </nav>
      <div>Socila Media links</div>
    </header>
  );
}
export default Header;
