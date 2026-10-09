import "./style.css";

const CLIENT_ERROR_COPY = {
  400: {
    eyebrow: "BAD REQUEST",
    title: "요청을 이해하지 못했어요.",
    message: "입력한 주소나 요청 내용을 다시 확인해 주세요.",
  },
  401: {
    eyebrow: "UNAUTHORIZED",
    title: "로그인이 필요한 페이지예요.",
    message: "로그인한 뒤 다시 시도해 주세요.",
  },
  403: {
    eyebrow: "ACCESS DENIED",
    title: "여기는 들어갈 수 없어요.",
    message: "이 페이지에 접근할 권한이 없습니다.",
  },
  404: {
    eyebrow: "NOT FOUND",
    title: "페이지를 찾지 못했어요.",
    message: "주소가 바뀌었거나 삭제된 페이지일 수 있어요.",
  },
};

function ClientError({ status = 404, title, message }) {
  const error = CLIENT_ERROR_COPY[status] ?? CLIENT_ERROR_COPY[400];

  return (
    <main className="errorPage">
      <section className="errorPanel" aria-labelledby="client-error-title">
        <p className="errorEyebrow">{error.eyebrow}</p>
        <strong className="errorCode">{status}</strong>
        <h1 id="client-error-title">{title ?? error.title}</h1>
        <p className="errorMessage">{message ?? error.message}</p>
        <div className="errorActions">
          <a className="errorPrimaryAction" href="/">
            홈으로 돌아가기
          </a>
          <button className="errorSecondaryAction" type="button" onClick={() => history.back()}>
            이전 페이지
          </button>
        </div>
      </section>
    </main>
  );
}

export default ClientError;
