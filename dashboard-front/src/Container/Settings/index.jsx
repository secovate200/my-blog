import { useState } from "react";
import { FaCheck, FaShieldHalved, FaUser } from "react-icons/fa6";
import { ContentHeader } from "../../components/Layout/ContentHeader";
import "./style.css";

export const SettingsContent = ({ theme, onToggleTheme }) => {
  const [account, setAccount] = useState({ name: "Secovate", email: "secovate200@example.com", github: "secovate200" });
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [message, setMessage] = useState("");

  const updateAccount = ({ target }) => {
    setAccount((value) => ({ ...value, [target.name]: target.value }));
    setMessage("");
  };
  const updatePassword = ({ target }) => {
    setPasswords((value) => ({ ...value, [target.name]: target.value }));
    setMessage("");
  };
  const saveAccount = (event) => {
    event.preventDefault();
    setMessage("계정 정보가 저장되었습니다.");
  };
  const changePassword = (event) => {
    event.preventDefault();
    if (passwords.next.length < 8) return setMessage("새 비밀번호는 8자 이상이어야 합니다.");
    if (passwords.next !== passwords.confirm) return setMessage("새 비밀번호가 일치하지 않습니다.");
    setPasswords({ current: "", next: "", confirm: "" });
    setMessage("비밀번호가 변경되었습니다.");
  };

  return (
    <main className="content settings-content">
      <ContentHeader title="설정" theme={theme} onToggleTheme={onToggleTheme} />
      <section className="settings-panel" aria-labelledby="account-settings-title">
        <div className="settings-panel--header">
          <div className="settings-avatar" aria-hidden="true"><FaUser /></div>
          <div className="settings-heading-copy">
            <p className="settings-eyebrow">승인된 계정</p>
            <h2 id="account-settings-title">{account.name}</h2>
            <p>{account.email}</p>
          </div>
          <span className="approval-badge"><FaCheck /> 승인됨</span>
        </div>

        <div className="permission-card">
          <span className="permission-card--icon" aria-hidden="true"><FaShieldHalved /></span>
          <div><span>권한</span><strong>관리자</strong><small>게시글, 사용자, 가입 승인 및 블로그 설정을 모두 관리할 수 있습니다.</small></div>
        </div>

        <div className="settings-sections">
          <form className="settings-form" onSubmit={saveAccount}>
            <div className="settings-form--title"><h3>계정 정보</h3><p>블로그에 표시되는 이름과 GitHub 계정을 수정합니다.</p></div>
            <div className="settings-form--grid">
              <label className="settings-field"><span>이름</span><input name="name" value={account.name} onChange={updateAccount} autoComplete="name" required /></label>
              <label className="settings-field"><span>이메일</span><input value={account.email} readOnly aria-describedby="email-help" /><small id="email-help">이메일은 이 페이지에서 변경할 수 없습니다.</small></label>
              <label className="settings-field settings-field--wide"><span>GitHub 사용자명</span><input name="github" value={account.github} onChange={updateAccount} placeholder="GitHub 사용자명" /></label>
            </div>
            <div className="settings-form--actions"><button className="settings-save" type="submit">정보 저장</button></div>
          </form>

          <form className="settings-form" onSubmit={changePassword}>
            <div className="settings-form--title"><h3>비밀번호 변경</h3><p>새 비밀번호는 8자 이상으로 입력해 주세요.</p></div>
            <div className="settings-form--grid">
              <label className="settings-field settings-field--wide"><span>현재 비밀번호</span><input name="current" type="password" value={passwords.current} onChange={updatePassword} autoComplete="current-password" required /></label>
              <label className="settings-field"><span>새 비밀번호</span><input name="next" type="password" value={passwords.next} onChange={updatePassword} autoComplete="new-password" required /></label>
              <label className="settings-field"><span>새 비밀번호 확인</span><input name="confirm" type="password" value={passwords.confirm} onChange={updatePassword} autoComplete="new-password" required /></label>
            </div>
            <div className="settings-form--actions"><button className="settings-save" type="submit">비밀번호 변경</button></div>
          </form>
        </div>
        <p className="settings-message" role="status" aria-live="polite">{message}</p>
      </section>
    </main>
  );
};
