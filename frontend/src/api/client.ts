import type { components } from "./schema";

type Schemas = components["schemas"];

export type User = Schemas["UserOut"];
export type EntrySummary = Schemas["EntrySummaryOut"];
export type LockedEntry = Schemas["LockedEntryOut"];
export type EntryListItem = EntrySummary | LockedEntry;
export interface EntryFilters {
  type?: string;
  q?: string;
  track?: string;
  phase?: string;
  region?: string;
}
export type EntryDetail = Schemas["EntryDetailOut"];
export type EntryType = Schemas["Type"];
export type Quiz = Schemas["QuizOut"];
export type QuizQuestion = Schemas["QuestionOut"];
export type QuizAnswer = Schemas["AnswerIn"]["answer"];
export type Timeline = Schemas["TimelineOut"];
export type TimelineEvent = Timeline["events"][number];
export type Dashboard = Schemas["DashboardOut"];
export type Profile = Schemas["ProfileOut"];
export type Session = Schemas["SessionOut"];
export type SessionStep = Session["steps"][number];
export type ReviewResult = Schemas["ReviewResultOut"];
export type Check = Schemas["CheckOut"];
export type CheckResult = Schemas["CheckResultOut"];
export type PracticeResult = Schemas["PracticeResultOut"];
export type DailyChallenge = Schemas["DailyChallengeOut"];
export type ChallengeResult = Schemas["ChallengeResultOut"];
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
  entries(filters: EntryFilters = {}) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value) params.set(key, value);
    }
    const query = params.toString();
    return request<EntryListItem[]>(`/entries${query ? `?${query}` : ""}`);
  },
  search: (q: string) => request<EntryListItem[]>(`/search?q=${encodeURIComponent(q)}`),
  entry: (slug: string) =>
    request<EntryDetail | LockedEntry>(`/entries/${encodeURIComponent(slug)}`),
  finishedReading: (slug: string) =>
    request<Schemas["ProgressOut"]>(`/entries/${encodeURIComponent(slug)}/finished-reading`, {
      method: "POST",
    }),
  startQuiz: (slug: string) =>
    request<Quiz>(`/entries/${encodeURIComponent(slug)}/quiz`, { method: "POST" }),
  timeline: () => request<Timeline>("/timeline"),
  dashboard: () => request<Dashboard>("/dashboard"),
  profile: () => request<Profile>("/profile"),
  session: () => request<Session>("/session"),
  review: () => request<Schemas["ReviewQueueOut"]>("/review"),
  answerReview: (question_id: number, answer: QuizAnswer) =>
    request<ReviewResult>("/review/answer", {
      method: "POST",
      body: JSON.stringify({ question_id, answer }),
    }),
  check: (id: number) => request<Check>(`/checks/${id}`),
  submitCheck: (id: number, answers: Schemas["AnswerIn"][]) =>
    request<CheckResult>(`/checks/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
  practice(filters: { track?: number; phase?: number; count?: number }) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined) params.set(key, String(value));
    }
    return request<Schemas["PracticeOut"]>(`/practice?${params}`);
  },
  answerPractice: (question_id: number, answer: QuizAnswer) =>
    request<PracticeResult>("/practice/answer", {
      method: "POST",
      body: JSON.stringify({ question_id, answer }),
    }),
  dailyChallenge: () => request<DailyChallenge>("/daily-challenge"),
  answerChallenge: (question_id: number, answer: QuizAnswer) =>
    request<ChallengeResult>("/daily-challenge/answer", {
      method: "POST",
      body: JSON.stringify({ question_id, answer }),
    }),
  submitQuiz: (attemptId: number, answers: Schemas["AnswerIn"][]) =>
    request<QuizResult>(`/quiz-attempts/${attemptId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
};
