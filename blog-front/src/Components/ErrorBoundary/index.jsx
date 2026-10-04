import { Component } from "react";
import { ServerError } from "../../Container/Error";

class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("Unexpected render error", error, info);
  }

  render() {
    if (this.state.hasError) {
      return <ServerError status={500} />;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
