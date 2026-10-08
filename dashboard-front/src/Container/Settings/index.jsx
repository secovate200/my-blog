import { useState } from "react";
import { FaCheck, FaShieldHalved, FaUser } from "react-icons/fa6";
import { changePassword as changeAccountPassword } from "../../api";
import { ContentHeader } from "../../components/Layout/ContentHeader";
import { navigateToErrorPage } from "../../utils/errorNavigation";
import "./style.css";

export const SettingsContent = ({ theme, onToggleTheme, user }) => {
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const updatePassword = ({ target }) => {
    setPasswords((value) => ({ ...value, [target.name]: target.value }));
    setMessage("");
  };
  const changePassword = async (event) => {
    event.preventDefault();
    if (passwords.next.length < 8) return setMessage("새 비밀번호는 8자 이상이어야 합니다.");
    if (passwords.next !== passwords.confirm) return setMessage("새 비밀번호가 일치하지 않습니다.");
    setSubmitting(true);
    setMessage("");
    try {
      const result = await changeAccountPassword({
        currentPassword: passwords.current,
        newPassword: passwords.next,
        newPasswordConfirm: passwords.confirm,
      });
      setPasswords({ current: "", next: "", confirm: "" });
      setMessage(result.detail);
    } catch (error) {
      if (error.status === 400) setMessage(error.message);
      else navigateToErrorPage(error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="content settings-content">
      <ContentHeader title="설정" theme={theme} onToggleTheme={onToggleTheme} />
      <section className="settings-panel" aria-labelledby="account-settings-title">
        <div className="settings-panel--header">
          <div className="settings-avatar" aria-hidden="true"><FaUser /></div>
          <div className="settings-heading-copy">
            <p className="settings-eyebrow">승인된 계정</p>
            <h2 id="account-settings-title">{user.name}</h2>
            <p>{user.email}</p>
          </div>
          <span className="approval-badge"><FaCheck /> 승인됨</span>
        </div>

        <div className="permission-card">
          <span className="permission-card--icon" aria-hidden="true"><FaShieldHalved /></span>
          <div><span>권한</span><strong>{user.role}</strong><small>승인된 계정에 부여된 권한으로 대시보드를 이용합니다.</small></div>
        </div>

        <div className="settings-sections">
          <section className="settings-form">
            <div className="settings-form--title"><h3>계정 정보</h3><p>등록된 계정 정보입니다. 이메일은 변경할 수 없습니다.</p></div>
            <div className="settings-form--grid">
              <label className="settings-field"><span>이름</span><input value={user.name} readOnly /></label>
              <label className="settings-field"><span>사용자명</span><input value={user.username} readOnly /></label>
              <label className="settings-field settings-field--wide"><span>이메일</span><input type="email" value={user.email} readOnly aria-describedby="email-help" /><small id="email-help">이메일은 이 페이지에서 변경할 수 없습니다.</small></label>
            </div>
          </section>

          <form className="settings-form" onSubmit={changePassword}>
            <div className="settings-form--title"><h3>비밀번호 변경</h3><p>새 비밀번호는 8자 이상으로 입력해 주세요.</p></div>
            <div className="settings-form--grid">
              <label className="settings-field settings-field--wide"><span>현재 비밀번호</span><input name="current" type="password" value={passwords.current} onChange={updatePassword} autoComplete="current-password" required /></label>
              <label className="settings-field"><span>새 비밀번호</span><input name="next" type="password" value={passwords.next} onChange={updatePassword} autoComplete="new-password" required /></label>
              <label className="settings-field"><span>새 비밀번호 확인</span><input name="confirm" type="password" value={passwords.confirm} onChange={updatePassword} autoComplete="new-password" required /></label>
            </div>
            <div className="settings-form--actions"><button className="settings-save" type="submit" disabled={submitting}>{submitting ? "변경 중..." : "비밀번호 변경"}</button></div>
          </form>
        </div>
        <p className="settings-message" role="status" aria-live="polite">{message}</p>
      </section>
    </main>
  );
};
