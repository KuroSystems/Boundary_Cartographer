import { render, screen } from '@testing-library/react';
import App from './App';

describe('App (S-01 smoke test)', () => {
  it('renders the placeholder heading', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /boundary cartographer/i })).toBeInTheDocument();
  });
});
