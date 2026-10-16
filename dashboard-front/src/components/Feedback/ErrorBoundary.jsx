/** 예기치 않은 렌더링 오류가 관리자 앱 전체를 빈 화면으로 만들지 않게 격리합니다. */
import { Component } from "react";
import { ServerError } from "../../Container/Error";

export class ErrorBoundary extends Component {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error, info) { console.error("관리자 화면 렌더링 중 오류가 발생했습니다.", error, info); }
  render() { return this.state.hasError ? <ServerError status={500} /> : this.props.children; }
}
