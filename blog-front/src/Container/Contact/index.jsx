import { useState } from "react";
import { FiMail, FiSend, FiUser } from "react-icons/fi";
import { createContactMessage } from "../../api/contact";
import Card from "../../Components/UI/Card";
import "./style.css";

function Contact() {
  const [status, setStatus] = useState("idle");

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus("submitting");
    const form = event.currentTarget;
    const formData = new FormData(form);

    try {
      await createContactMessage({
        name: formData.get("name"),
        email: formData.get("email"),
        message: formData.get("message"),
      });
      form.reset();
      setStatus("success");
    } catch {
      setStatus("error");
    }
  };

  const statusMessage = {
    idle: "모든 항목은 필수입니다.",
    submitting: "메시지를 보내는 중입니다…",
    success: "메시지가 접수되었습니다. 감사합니다.",
    error: "전송하지 못했습니다. 잠시 후 다시 시도해 주세요.",
  }[status];

  return (
    <Card>
      <section className="contact" aria-labelledby="contact-title">
        <header className="contactHeader">
          <span>Contact</span>
          <h1 id="contact-title">메시지를 남겨주세요</h1>
          <p>문의나 제안이 있다면 아래 내용을 작성해 주세요.</p>
        </header>

        <form
          className="contactForm"
          onSubmit={handleSubmit}
          onInput={() => status !== "submitting" && setStatus("idle")}
        >
          <div className="contactFields">
            <div className="formField">
              <label htmlFor="contact-name">이름</label>
              <div className="inputWrap">
                <FiUser aria-hidden="true" />
                <input
                  id="contact-name"
                  name="name"
                  type="text"
                  autoComplete="name"
                  maxLength={50}
                  placeholder="이름을 입력해 주세요"
                  required
                />
              </div>
            </div>

            <div className="formField">
              <label htmlFor="contact-email">이메일</label>
              <div className="inputWrap">
                <FiMail aria-hidden="true" />
                <input
                  id="contact-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  maxLength={254}
                  placeholder="name@example.com"
                  required
                />
              </div>
            </div>
          </div>

          <div className="formField">
            <label htmlFor="contact-message">내용</label>
            <textarea
              id="contact-message"
              name="message"
              rows={9}
              maxLength={2000}
              placeholder="내용을 입력해 주세요"
              required
            />
          </div>

          <div className="contactActions">
            <p className="formStatus" aria-live="polite">
              {statusMessage}
            </p>
            <button type="submit" disabled={status === "submitting"}>
              <FiSend aria-hidden="true" />
              {status === "submitting" ? "보내는 중" : "보내기"}
            </button>
          </div>
        </form>
      </section>
    </Card>
  );
}
export default Contact;
