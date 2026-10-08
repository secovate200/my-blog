import React from "react";
import { FaBook, FaBookmark } from "react-icons/fa";
import { FaFlask } from "react-icons/fa6";
export const Card = ({ onCategoryClick, onPostClick, onResearchClick, counts = {} }) => {
  const course = [
    { id: "category", title: "카테고리", count: counts.category ?? 0, icon: <FaBook /> },
    { id: "post", title: "게시글", count: counts.post ?? 0, icon: <FaBookmark /> },
    { id: "research", title: "연구 글", count: counts.research ?? 0, icon: <FaFlask /> },
  ];
  const handlers = {
    category: onCategoryClick,
    post: onPostClick,
    research: onResearchClick,
  };

  return (
    <div className="card--container">
      {course.map((item) => (
        <div
          className="card card--interactive"
          key={item.title}
          onClick={handlers[item.id]}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") handlers[item.id]?.();
          }}
          role="link"
          tabIndex={0}
        >
          <div className="card--cover">{item.icon}</div>
          <div className="card--title">
            <h2>{item.title}</h2>
            <strong className="card--count" aria-label={`${item.title} ${item.count}`}>
              {item.count}
            </strong>
          </div>
        </div>
      ))}
    </div>
  );
};
