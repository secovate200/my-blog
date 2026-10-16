/** 관리자 React 앱을 마운트하고 전역 오류 경계를 가장 바깥에 배치합니다. */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { App } from './App.jsx'
import { ErrorBoundary } from './components/Feedback/ErrorBoundary.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
