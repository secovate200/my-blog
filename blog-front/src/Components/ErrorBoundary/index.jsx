/** 렌더링 오류를 격리해 방문자에게 복구 가능한 안내 화면을 제공합니다. */
import { Component } from "react";
import { ServerError } from "../../Container/Error";

class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("화면 렌더링 중 예기치 않은 오류가 발생했습니다.", error, info);
  }

  render() {
    if (this.state.hasError) {
      return <ServerError status={500} />;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
