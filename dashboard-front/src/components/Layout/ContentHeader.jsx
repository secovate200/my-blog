import React from "react";
export const ContentHeader = ({ title = "Dashboard" }) => {
  return (
    <div className="content--header">
      <h1 className="header--title">{title}</h1>
    </div>
  );
};
