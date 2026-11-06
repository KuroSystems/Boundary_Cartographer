import { NavLink, Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient, apiMode } from '../api/selectClient';

const NAV = [
  { to: '/', label: 'Overview' },
  { to: '/graph', label: 'Graph' },
  { to: '/replay', label: 'Replay' },
  { to: '/policy', label: 'Policy' },
  { to: '/approvals', label: 'Approvals' },
  { to: '/evidence', label: 'Evidence' },
];

export function AppShell() {
  const scenario = useQuery({
    queryKey: ['scenario'],
    queryFn: () => apiClient.getScenario(),
  });

  return (
    <div>
      <header className="app-header">
        <h1>Boundary Cartographer</h1>
        <span className="chip offline">OFFLINE DEMO</span>
        {apiMode === 'fixture' && <span className="chip fixture">fixture data</span>}
        <span className="chip scenario">
          scenario: {scenario.data?.scenario_id ?? '…'}
        </span>
      </header>
      <nav className="app-nav">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => (isActive ? 'active' : '')}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
