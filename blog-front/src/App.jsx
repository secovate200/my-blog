import { useState } from "react";
import Home from "./Container/Home";
import Header from "./Components/Header";
import Hero from "./Components/Hero";
import "./App.css";

function App() {
  return (
    <div className="App">
      <Header />
      <Hero />
      <Home />
    </div>
  );
}

export default App;
