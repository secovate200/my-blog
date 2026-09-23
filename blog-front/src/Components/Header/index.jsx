import react from "react";
import "./style.css";
function Header(props) {
  return (
    <header className="header">
      <nav className="headerMenu">
        <a href="#">Home</a>
        <a href="#">Contact</a>
        <a href="#">Login</a>
        <a href="#">Dashboard</a>
      </nav>
    </header>
  );
}
export default Header;
