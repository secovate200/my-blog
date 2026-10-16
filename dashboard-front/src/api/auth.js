/** 인증 API의 입력 값을 서버 계약에 맞게 변환합니다. */
import { apiRequest } from "./client";

export async function getCurrentUser() {
  try {
    return await apiRequest("/blog/auth/me/");
  } catch (error) {
    // 앱 최초 진입 시 비로그인 상태는 정상 흐름이므로 오류 화면으로 보내지 않습니다.
    if (error.status === 401 || error.status === 403) return null;
    throw error;
  }
}

export async function login({ email, password }) {
  return apiRequest("/blog/auth/login/", {
    method: "POST",
    data: { email, password },
    requiresCsrf: true,
  });
}

export async function signup({ name, email, password }) {
  return apiRequest("/blog/auth/signup/", {
    method: "POST",
    data: { name, email, password },
    requiresCsrf: true,
  });
}

export async function logout() {
  return apiRequest("/blog/auth/logout/", {
    method: "POST",
    requiresCsrf: true,
  });
}

export async function changePassword({ currentPassword, newPassword, newPasswordConfirm }) {
  return apiRequest("/blog/auth/password/", {
    method: "POST",
    requiresCsrf: true,
    data: {
      current_password: currentPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    },
  });
}
