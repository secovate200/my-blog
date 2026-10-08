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
