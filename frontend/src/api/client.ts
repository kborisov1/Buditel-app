import type { components } from "./schema";

type Schemas = components["schemas"];

export type User = Schemas["UserOut"];
export type EntrySummary = Schemas["EntrySummaryOut"];
export type LockedEntry = Schemas["LockedEntryOut"];
export type EntryListItem = EntrySummary | LockedEntry;
export type EntryDetail = Schemas["EntryDetailOut"];
export type EntryType = Schemas["Type"];
export type Quiz = Schemas["QuizOut"];
export type QuizQuestion = Schemas["QuestionOut"];
export type QuizAnswer = Schemas["AnswerIn"]["answer"];
export type QuizResult = Schemas["QuizPassedOut"] | Schemas["QuizFailedOut"];

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
  entries(filters: { type?: string; q?: string } = {}) {
    const params = new URLSearchParams();
    if (filters.type) params.set("type", filters.type);
    if (filters.q) params.set("q", filters.q);
    const query = params.toString();
    return request<EntryListItem[]>(`/entries${query ? `?${query}` : ""}`);
  },
  entry: (slug: string) =>
    request<EntryDetail | LockedEntry>(`/entries/${encodeURIComponent(slug)}`),
  finishedReading: (slug: string) =>
    request<Schemas["ProgressOut"]>(`/entries/${encodeURIComponent(slug)}/finished-reading`, {
      method: "POST",
    }),
  startQuiz: (slug: string) =>
    request<Quiz>(`/entries/${encodeURIComponent(slug)}/quiz`, { method: "POST" }),
  submitQuiz: (attemptId: number, answers: Schemas["AnswerIn"][]) =>
    request<QuizResult>(`/quiz-attempts/${attemptId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
};
