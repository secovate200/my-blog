import { useEffect, useRef } from "react";
import Typed from "typed.js";
import "./style.css";

function Logo() {
  const logoText = useRef(null);

  useEffect(() => {
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    if (reduceMotion) {
      logoText.current.textContent = "SECOVATE200 BLOG";
      return undefined;
    }

    const typed = new Typed(logoText.current, {
      strings: ["SECOVATE200 BLOG"],
      typeSpeed: 85,
      startDelay: 300,
      showCursor: true,
      cursorChar: "_",
      loop: false,
    });

    return () => typed.destroy();
  }, []);

  return (
    <div className="logo" aria-label="SECOVATE200 BLOG">
      <span ref={logoText} aria-hidden="true" />
    </div>
  );
}
export default Logo;
