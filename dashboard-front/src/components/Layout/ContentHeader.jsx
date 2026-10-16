/** 모든 관리자 페이지가 같은 제목 구조와 접근성을 사용하도록 헤더를 표준화합니다. */
import React from "react";
export const ContentHeader = ({ title = "Dashboard" }) => {
  return (
    <div className="content--header">
      <h1 className="header--title">{title}</h1>
    </div>
  );
};
