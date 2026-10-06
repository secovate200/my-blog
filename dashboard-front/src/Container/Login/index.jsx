import { useState } from "react";
import { FaArrowLeft, FaEye, FaEyeSlash, FaLock, FaMoon, FaSun, FaUser } from "react-icons/fa6";
import blogLogo from "../../assets/logo.png";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import "./style.css";

export function LoginContent({ theme, onToggleTheme, onLogin }) {
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setSubmitting(true);
    setMessage("");
    try {
      await onLogin({ account: data.get("account"), password: data.get("password"), remember: false });
    } catch (error) {
      if (error.status === 400) setMessage(error.message);
      else navigateToErrorPage(error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-screen">
      <header className="login-toolbar">
        <a href="http://127.0.0.1:5173"><FaArrowLeft aria-hidden="true" /> 블로그로 돌아가기</a>
        <button type="button" onClick={onToggleTheme} aria-label={theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환"}>
          {theme === "dark" ? <FaSun /> : <FaMoon />}
        </button>
      </header>
      <section className="login-card" aria-labelledby="login-title">
        <a className="login-blog-logo" href="http://127.0.0.1:5173" aria-label="SECOVATE200 BLOG 홈"><img src={blogLogo} alt="SECOVATE200 Bug Hunter" /></a>
        <div className="login-copy"><h1 id="login-title">로그인</h1></div>
        <form onSubmit={submit}>
          <label className="login-input"><FaUser aria-hidden="true" /><input name="account" type="text" autoComplete="username" placeholder="아이디 또는 이메일" required /></label>
          <label className="login-input"><FaLock aria-hidden="true" /><input name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="비밀번호" required /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "비밀번호 숨기기" : "비밀번호 보기"}>{showPassword ? <FaEyeSlash /> : <FaEye />}</button></label>
          <button className="login-submit" type="submit" disabled={submitting}>{submitting ? "확인 중..." : "로그인"}</button>
          <p className="login-message" role="status" aria-live="polite">{message}</p>
        </form>
      </section>
    </main>
  );
}

