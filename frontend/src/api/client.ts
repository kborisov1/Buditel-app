import type { components } from "./schema";

export type User = components["schemas"]["UserOut"];

export class ApiError extends Error {
  status: number;
  constructor(status: number) {
    super(`API error ${status}`);
    this.status = status;
  }
}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken(),
      ...init.headers,
    },
  });
  if (!response.ok) throw new ApiError(response.status);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const api = {
  me: () => request<User>("/auth/me"),
  async login(email: string, password: string): Promise<User> {
    await request<void>("/auth/csrf"); // makes sure the CSRF cookie exists
    return request<User>("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      }),
    });
  },
  logout: () => request<void>("/auth/logout", { method: "POST" }),
};
