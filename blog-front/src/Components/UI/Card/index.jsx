/** 카드의 공통 시각 구조를 제공해 콘텐츠 컴포넌트가 의미 표현에 집중하게 합니다. */
import React from "react";
import "./style.css";
function Card(props) {
  return <div className="card">{props.children}</div>;
}
export default Card;
