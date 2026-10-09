import { Component } from "react";
import { ServerError } from "../../Container/Error";

export class ErrorBoundary extends Component {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error, info) { console.error("Dashboard render error", error, info); }
  render() { return this.state.hasError ? <ServerError status={500} /> : this.props.children; }
}
