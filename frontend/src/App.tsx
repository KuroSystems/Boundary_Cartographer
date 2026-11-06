import { Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { RouteErrorBoundary } from './components/RouteErrorBoundary';
import { OverviewPage } from './pages/OverviewPage';
import { GraphPage } from './pages/GraphPage';
import { ReplayPage } from './pages/ReplayPage';
import { PolicyPage } from './pages/PolicyPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { EvidencePage } from './pages/EvidencePage';

export default function App() {
  return (
    <RouteErrorBoundary>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<OverviewPage />} />
          <Route path="graph" element={<GraphPage />} />
          <Route path="replay" element={<ReplayPage />} />
          <Route path="policy" element={<PolicyPage />} />
          <Route path="approvals" element={<ApprovalsPage />} />
          <Route path="evidence" element={<EvidencePage />} />
          <Route path="*" element={<p>Route not found.</p>} />
        </Route>
      </Routes>
    </RouteErrorBoundary>
  );
}
