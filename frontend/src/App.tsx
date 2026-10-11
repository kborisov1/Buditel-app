import { Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";
import LoginPage from "./features/auth/LoginPage";
import { useMe } from "./features/auth/useAuth";
import DashboardPage from "./features/dashboard/DashboardPage";
import EntryPage from "./features/entry/EntryPage";
import LibraryPage from "./features/library/LibraryPage";
import ChallengePage from "./features/challenge/ChallengePage";
import CheckPage from "./features/check/CheckPage";
import PracticePage from "./features/practice/PracticePage";
import ProfilePage from "./features/profile/ProfilePage";
import ReviewPage from "./features/review/ReviewPage";
import SessionPage from "./features/session/SessionPage";
import QuizPage from "./features/quiz/QuizPage";
import TimelinePage from "./features/timeline/TimelinePage";

export default function App() {
  const me = useMe();

  if (me.isPending) return null;
  if (!me.data) return <LoginPage />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="entries/:slug" element={<EntryPage />} />
        <Route path="entries/:slug/quiz" element={<QuizPage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="session" element={<SessionPage />} />
        <Route path="checks/:id" element={<CheckPage />} />
        <Route path="practice" element={<PracticePage />} />
        <Route path="challenge" element={<ChallengePage />} />
        <Route path="profile" element={<ProfilePage />} />
      </Route>
    </Routes>
  );
}
