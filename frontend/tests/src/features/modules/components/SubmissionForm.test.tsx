import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SubmissionForm } from '../../../../../src/features/modules/components/SubmissionForm';

describe('SubmissionForm', () => {
  it('requires source material before submission', () => {
    const submit = vi.fn(async () => null);
    render(<SubmissionForm busy={false} onSubmit={submit} />);
    fireEvent.click(screen.getByRole('button', { name: /create module/i }));
    expect(screen.getByRole('alert')).toHaveTextContent('Add a task description');
    expect(submit).not.toHaveBeenCalled();
  });

  it('rejects unsupported documents before calling the API', () => {
    const submit = vi.fn(async () => null);
    render(<SubmissionForm busy={false} onSubmit={submit} />);
    fireEvent.click(screen.getByRole('tab', { name: /upload a document/i }));
    fireEvent.change(document.querySelector('input[type=file]')!, { target: { files: [new File(['x'], 'incident.docx')] } });
    expect(screen.getByRole('alert')).toHaveTextContent('Choose a .txt, .md, or text-based .pdf');
    expect(submit).not.toHaveBeenCalled();
  });

  it('submits the sample RCA as source text', async () => {
    const submit = vi.fn(async () => null);
    render(<SubmissionForm busy={false} onSubmit={submit} />);
    fireEvent.click(screen.getByRole('button', { name: /try a sample RCA/i }));
    fireEvent.click(screen.getByRole('button', { name: /create module/i }));
    expect(submit).toHaveBeenCalledWith({ text: expect.stringContaining('duplicate orders from webhook retries') });
  });
});
