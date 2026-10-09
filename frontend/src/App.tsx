import { Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";
import LoginPage from "./features/auth/LoginPage";
import { useMe } from "./features/auth/useAuth";
import DashboardPage from "./features/dashboard/DashboardPage";
import EntryPage from "./features/entry/EntryPage";
import LibraryPage from "./features/library/LibraryPage";
import PlaceholderPage from "./features/placeholder/PlaceholderPage";
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
        <Route path="practice" element={<PlaceholderPage name="practice" />} />
        <Route path="profile" element={<PlaceholderPage name="profile" />} />
      </Route>
    </Routes>
  );
}
