import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { createQueryClient } from './api/queryClient';

function renderApp(route = '/') {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('App shell (FE-01 smoke test)', () => {
  it('renders the header with OFFLINE DEMO chip and fixture indicator', async () => {
    renderApp();
    expect(
      screen.getByRole('heading', { name: /boundary cartographer/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/offline demo/i)).toBeInTheDocument();
    // VITE_API_MODE is unset in tests -> fixture mode indicator is visible
    expect(screen.getByText(/fixture data/i)).toBeInTheDocument();
  });

  it('renders navigation for all six routes', () => {
    renderApp();
    for (const label of ['Overview', 'Graph', 'Replay', 'Policy', 'Approvals', 'Evidence']) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument();
    }
  });

  it('renders the overview route with fixture data and no server', async () => {
    renderApp('/');
    expect(await screen.findByTestId('path-table')).toBeInTheDocument();
    expect(screen.getByText('P1')).toBeInTheDocument();
    expect(screen.getAllByText('blocked').length).toBeGreaterThan(0);
  });

  it('renders the replay route with fixture replay events', async () => {
    renderApp('/replay');
    expect(await screen.findByText(/replay events/i)).toBeInTheDocument();
    expect(screen.getAllByText(/finance\.export/).length).toBeGreaterThan(0);
  });

  it('renders the remaining routes', async () => {
    renderApp('/graph');
    expect(await screen.findByText(/attack-path graph/i)).toBeInTheDocument();
    renderApp('/policy');
    expect(await screen.findByText(/policy diff/i)).toBeInTheDocument();
    renderApp('/approvals');
    expect((await screen.findAllByText(/approval queue/i)).length).toBeGreaterThan(0);
    renderApp('/evidence');
    expect(await screen.findByText(/evidence chain/i)).toBeInTheDocument();
  });
});
