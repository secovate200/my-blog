import React from "react";
import "./style.css";
import Card from "../UI/Card/Card";
import Logo from "../Logo/Logo";
import Navbar from "../Navbar/Navbar";
function Hero(props) {
  return (
    <div className="hero">
      <Card>
        <div style={{ padding: "50px 0" }}>
          <Logo />
        </div>
        <Navbar />
      </Card>
    </div>
  );
}
export default Hero;
