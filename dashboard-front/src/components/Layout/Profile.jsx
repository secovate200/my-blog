import {
  FaHouseUser,
  FaPen,
  FaRightFromBracket,
  FaShieldHalved,
  FaUser,
} from "react-icons/fa6";
import { FaMoon, FaSearch, FaSun } from "react-icons/fa";
import "./Profile.css";

export const Profile = ({
  name = "Secovate",
  role = "Administrator",
  onWritePost = () => {},
  onMyPage = () => {},
  onLogout = () => {},
  onSearch = () => {},
  searchQuery = "",
  canAccessAdmin = false,
  canWritePost = false,
  theme = "light",
  onToggleTheme = () => {},
}) => {
  const submitSearch = (event) => {
    event.preventDefault();
    onSearch(new FormData(event.currentTarget).get("query").trim());
  };

  return (
    <aside className="profile" aria-label="Profile and quick actions">
      <div className="profile--tools">
        <form className="profile-search" role="search" onSubmit={submitSearch}>
          <span className="visually-hidden">게시글 검색</span>
          <input key={searchQuery} name="query" type="search" defaultValue={searchQuery} placeholder="게시글 검색..." />
          <button type="submit" aria-label="게시글 검색"><FaSearch aria-hidden="true" /></button>
        </form>
        <button
          className="profile-theme-toggle"
          type="button"
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환"}
          aria-pressed={theme === "dark"}
        >
          {theme === "dark" ? <FaSun /> : <FaMoon />}
        </button>
      </div>
      <div className="profile--card">
        <div className="profile--avatar" aria-hidden="true">
          <FaUser />
        </div>
        <div className="profile--identity">
          <strong>{name}</strong>
          <span>{role}</span>
        </div>
      </div>

      <div className="quick-actions">
        <p className="quick-actions--label">Quick actions</p>
        {canWritePost && <a className="quick-action" href="#/write" onClick={onWritePost}>
          <span className="quick-action--icon">
            <FaPen aria-hidden="true" />
          </span>
          <span>
            <strong>글쓰기</strong>
            <small>새 게시글 작성</small>
          </span>
        </a>}
        <a className="quick-action" href="#/settings" onClick={onMyPage}>
          <span className="quick-action--icon">
            <FaHouseUser aria-hidden="true" />
          </span>
          <span>
            <strong>내 계정</strong>
            <small>계정 정보 및 비밀번호 관리</small>
          </span>
        </a>
        {canAccessAdmin && (
          <a className="quick-action" href="/admin/">
            <span className="quick-action--icon">
              <FaShieldHalved aria-hidden="true" />
            </span>
            <span>
              <strong>Django Admin</strong>
              <small>백엔드 관리자 화면</small>
            </span>
          </a>
        )}
        <button className="quick-action quick-action--logout" type="button" onClick={onLogout}>
          <span className="quick-action--icon">
            <FaRightFromBracket aria-hidden="true" />
          </span>
          <span>
            <strong>로그아웃</strong>
            <small>관리자 세션 종료</small>
          </span>
        </button>
      </div>
    </aside>
  );
};
