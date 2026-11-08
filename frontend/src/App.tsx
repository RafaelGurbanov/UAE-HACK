import { Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { AboutPage } from './pages/AboutPage';
import { AuditPage } from './pages/AuditPage';
import { GapsPage } from './pages/GapsPage';
import { EntryDetailPage, LawDetailPage } from './pages/LawDetailPage';
import { LawsPage } from './pages/LawsPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ScenarioPage } from './pages/ScenarioPage';
import { SearchPage } from './pages/SearchPage';

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<SearchPage />} />
        <Route path="laws" element={<LawsPage />} />
        <Route path="laws/entry/:id" element={<EntryDetailPage />} />
        <Route path="laws/:id" element={<LawDetailPage />} />
        <Route path="scenario" element={<ScenarioPage />} />
        <Route path="gaps" element={<GapsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
