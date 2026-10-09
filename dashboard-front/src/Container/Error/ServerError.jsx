import "./style.css";

function ServerError({
  status = 500,
  title = "서버가 잠시 멈췄어요.",
  message = "문제를 확인하고 있습니다. 잠시 후 다시 시도해 주세요.",
}) {
  return (
    <main className="errorPage errorPageServer">
      <section className="errorPanel" aria-labelledby="server-error-title">
        <p className="errorEyebrow">SERVER ERROR</p>
        <strong className="errorCode">{status}</strong>
        <div className="serverSignal" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
        <h1 id="server-error-title">{title}</h1>
        <p className="errorMessage">{message}</p>
        <div className="errorActions">
          <button className="errorPrimaryAction" type="button" onClick={() => location.reload()}>
            다시 시도하기
          </button>
          <a className="errorSecondaryAction" href="/">
            홈으로 돌아가기
          </a>
        </div>
      </section>
    </main>
  );
}

export default ServerError;
