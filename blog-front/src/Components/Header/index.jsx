/** 로고와 탐색 메뉴를 묶어 모든 공개 페이지에 일관된 상단 영역을 제공합니다. */
import "./style.css";

const dashboardUrl = (
  import.meta.env.VITE_DASHBOARD_URL ?? "http://localhost:5175"
).replace(/\/$/, "");

function Header() {
  return (
    <header className="header">
      <nav className="headerMenu">
        <a href={`${dashboardUrl}/#/login`}>Login</a>
        <a href={`${dashboardUrl}/#/dashboard`}>Dashboard</a>
      </nav>
    </header>
  );
}
export default Header;
