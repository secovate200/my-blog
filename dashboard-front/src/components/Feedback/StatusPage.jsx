import { FaArrowLeft, FaArrowRotateRight, FaBan, FaGaugeHigh, FaHouse, FaLock, FaTriangleExclamation } from "react-icons/fa6";
import "./StatusPage.css";

const statusContent = {
  401: { eyebrow: "AUTHENTICATION REQUIRED", title: "인증 정보가 필요합니다", description: "현재 요청을 처리할 인증 정보를 확인할 수 없습니다.", hint: "대시보드로 돌아간 뒤 다시 시도해 주세요.", icon: FaLock },
  403: { eyebrow: "ACCESS DENIED", title: "접근할 수 없는 기능입니다", description: "현재 환경에서는 요청한 관리 기능을 사용할 수 없습니다.", hint: "접근 가능한 메뉴를 이용하거나 관리자에게 권한을 확인해 주세요.", icon: FaBan },
  404: { eyebrow: "PAGE NOT FOUND", title: "페이지를 찾지 못했습니다", description: "요청한 주소가 변경됐거나 더 이상 존재하지 않습니다.", hint: "주소를 다시 확인하거나 대시보드에서 원하는 메뉴를 선택해 주세요.", icon: FaTriangleExclamation },
  429: { eyebrow: "TOO MANY REQUESTS", title: "잠시 쉬어가야 합니다", description: "짧은 시간에 요청이 너무 많이 전달됐습니다.", hint: "잠시 기다린 뒤 페이지를 다시 불러와 주세요.", icon: FaGaugeHigh },
  500: { eyebrow: "SYSTEM ERROR", title: "화면을 불러오지 못했습니다", description: "요청을 처리하던 중 예상하지 못한 문제가 발생했습니다.", hint: "새로고침해도 문제가 계속되면 잠시 후 다시 시도해 주세요.", icon: FaTriangleExclamation },
};

export const StatusPage = ({ code = 500 }) => {
  const status = statusContent[code] ?? statusContent[500];
  const StatusIcon = status.icon;
  const canReload = [429, 500].includes(code);

  return (
    <main className={`dashboard-status dashboard-status--${code}`}>
      <section className="dashboard-status-card" aria-labelledby="status-title">
        <div className="dashboard-status-visual" aria-hidden="true">
          <span className="dashboard-status-icon"><StatusIcon /></span>
          <strong>{code}</strong>
          <span className="dashboard-status-grid" />
        </div>
        <div className="dashboard-status-copy">
          <p>{status.eyebrow}</p>
          <h1 id="status-title">{status.title}</h1>
          <span>{status.description}</span>
          <small>{status.hint}</small>
          <div className="dashboard-status-actions">
            <a href="#/dashboard"><FaHouse aria-hidden="true" /> 대시보드로</a>
            {canReload ? (
              <button type="button" onClick={() => window.location.reload()}><FaArrowRotateRight aria-hidden="true" /> 새로고침</button>
            ) : (
              <button type="button" onClick={() => window.history.back()}><FaArrowLeft aria-hidden="true" /> 이전 화면</button>
            )}
          </div>
        </div>
      </section>
      <footer className="dashboard-status-footer"><strong>SECOVATE</strong><span>ADMIN DASHBOARD · ERROR {code}</span></footer>
    </main>
  );
};

