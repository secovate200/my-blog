/** 사용자 권한에 맞는 메뉴만 노출해 접근 불가능한 화면 이동을 예방합니다. */
import React from "react";
import { FaHome, FaBookmark, FaBook } from "react-icons/fa";
import { FaFlask, FaGear } from "react-icons/fa6";
import "./Sidebar.css";
export const Sidebar = ({ currentPage = "dashboard", permissions = {} }) => {
  return (
    <div className="menu">
      <div className="logo">
        <FaBookmark className="logo-icon" />
        <h2>Secovate200</h2>
      </div>

      <div className="menu--list">
        <a href="#/dashboard" className={`item ${currentPage === "dashboard" ? "item--active" : ""}`}>
          <FaHome className="icon" />
          Dashboard
        </a>
        {permissions.viewPosts && <a href="#/blog" className={`item ${currentPage === "blog" ? "item--active" : ""}`}>
          <FaBook className="icon" />
          Blog
        </a>}
        {permissions.viewProjects && permissions.viewResearchPosts && <a href="#/research" className={`item ${currentPage === "research" ? "item--active" : ""}`}>
          <FaFlask className="icon" />
          연구 관리
        </a>}
        <a href="#/settings" className={`item ${currentPage === "settings" ? "item--active" : ""}`}>
          <FaGear className="icon" />
          Settings
        </a>
      </div>
    </div>
  );
};
