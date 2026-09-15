const TOKEN_KEY = 'dingdong_admin_token'
const ROLE_KEY = 'dingdong_admin_role'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getRole() {
  return localStorage.getItem(ROLE_KEY) || 'admin'
}

export function setRole(role) {
  localStorage.setItem(ROLE_KEY, role)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
}
