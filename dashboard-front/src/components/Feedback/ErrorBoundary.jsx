import { Component } from "react";
import { StatusPage } from "./StatusPage";

export class ErrorBoundary extends Component {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error, info) { console.error("Dashboard render error", error, info); }
  render() { return this.state.hasError ? <StatusPage code={500} /> : this.props.children; }
}
