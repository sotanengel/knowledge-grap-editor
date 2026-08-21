import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { App } from './App';

describe('App', () => {
  it('renders the product name', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: 'OntoForge' })).toBeInTheDocument();
  });

  it('renders a main region for the editor', () => {
    render(<App />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
