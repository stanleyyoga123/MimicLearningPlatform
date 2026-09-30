import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it } from 'vitest';
import { JuniorProfilePage } from '../../../../src/pages/junior/JuniorProfilePage';
import { MentorPage } from '../../../../src/pages/mentor/MentorPage';

const saved = new Map<string, string>();
beforeEach(() => {
  saved.clear();
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => saved.get(key) ?? null,
      setItem: (key: string, value: string) => { saved.set(key, value); },
    },
  });
});

it('hides sidebar navigation and restores it after expanding', () => {
  render(<JuniorProfilePage />);

  const toggle = screen.getByRole('button', { name: 'Collapse sidebar' });
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  fireEvent.click(toggle);

  expect(screen.getByRole('button', { name: 'Expand sidebar' })).toHaveAttribute('aria-expanded', 'false');
  expect(document.getElementById('mimic-sidebar')).toHaveAttribute('hidden');
  expect(screen.queryByRole('link', { name: 'Available tasks' })).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Expand sidebar' }));
  expect(screen.getByRole('link', { name: 'Available tasks' })).toBeInTheDocument();
});

it('keeps the collapsed choice when another page mounts', () => {
  const first = render(<JuniorProfilePage />);
  fireEvent.click(screen.getByRole('button', { name: 'Collapse sidebar' }));
  first.unmount();

  render(<MentorPage />);

  expect(screen.getByRole('button', { name: 'Expand sidebar' })).toHaveAttribute('aria-expanded', 'false');
  expect(document.getElementById('mimic-sidebar')).toHaveAttribute('hidden');
});
