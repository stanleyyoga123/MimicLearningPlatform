import { useRef, useState, type ChangeEvent, type FormEvent } from 'react';
import { ArrowUpRight, FileText, Sparkles, UploadCloud, X } from 'lucide-react';

const SAMPLE_RCA = `Root cause analysis: duplicate orders from webhook retries

Our order service receives payment.succeeded webhooks from a payment provider. The provider retries delivery when it does not receive a quick acknowledgement. On 12 May, a short network timeout caused the same event to be delivered three times. The handler inserted a new order for every delivery because it did not check whether the event ID had already been processed.

Expected behavior: processing the same payment event more than once should create exactly one order. A distinct event should still create its own order. The API should acknowledge repeat deliveries without duplicating data. Keep the exercise small and self-contained; simulate the payment provider locally.`;

type SubmissionFormProps = {
  busy: boolean;
  onSubmit: (input: { text?: string; file?: File }) => Promise<string | null>;
};

export function SubmissionForm({ busy, onSubmit }: SubmissionFormProps) {
  const [mode, setMode] = useState<'text' | 'file'>('text');
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectFile = (candidate: File | undefined) => {
    if (!candidate) return;
    const extension = candidate.name.split('.').pop()?.toLowerCase();
    if (!extension || !['txt', 'md', 'pdf'].includes(extension)) {
      setError('Choose a .txt, .md, or text-based .pdf document.');
      setFile(null);
      return;
    }
    if (candidate.size > 10 * 1024 * 1024) {
      setError('The document must be 10 MB or smaller.');
      setFile(null);
      return;
    }
    setError(null);
    setFile(candidate);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => selectFile(event.target.files?.[0]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mode === 'text' && !text.trim()) { setError('Add a task description or RCA to begin.'); return; }
    if (mode === 'text' && text.length > 50_000) { setError('Keep the description under 50,000 characters.'); return; }
    if (mode === 'file' && !file) { setError('Choose a document to begin.'); return; }
    setError(await onSubmit(mode === 'text' ? { text: text.trim() } : { file: file! }));
  };

  return (
    <section className="submission-view" aria-labelledby="submission-title">
      <div className="hero-label"><span className="small-line" /> THE WORKSHOP · MODULE CREATOR</div>
      <div className="hero-row">
        <div>
          <h1 id="submission-title">Turn real work into<br /><em>real learning.</em></h1>
          <p className="hero-copy">Bring a task, job brief, or incident report. Mimic turns it into a focused backend engineering exercise with a real codebase, a verified solution, and teammates to learn from.</p>
        </div>
        <div className="hero-mark" aria-hidden="true"><span>M</span><i /></div>
      </div>

      <div className="workspace-grid">
        <div className="editor-card">
          <div className="card-head"><div><span className="eyebrow">01 / SOURCE MATERIAL</span><h2>What should they work on?</h2></div><span className="card-head-icon"><FileText size={19} /></span></div>
          <form onSubmit={handleSubmit} noValidate>
            <div className="mode-tabs" role="tablist" aria-label="Input type">
              <button type="button" role="tab" aria-selected={mode === 'text'} className={mode === 'text' ? 'active' : ''} onClick={() => { setMode('text'); setError(null); }}><FileText size={15} /> Paste a brief</button>
              <button type="button" role="tab" aria-selected={mode === 'file'} className={mode === 'file' ? 'active' : ''} onClick={() => { setMode('file'); setError(null); }}><UploadCloud size={16} /> Upload a document</button>
            </div>
            {mode === 'text' ? (
              <div className="text-input-wrap">
                <label className="sr-only" htmlFor="source-text">Task description or RCA</label>
                <textarea id="source-text" value={text} onChange={(event) => { setText(event.target.value); setError(null); }} placeholder="Describe the problem, expected behavior, and any context from your project…" aria-describedby="text-hint" />
                <div className="text-foot"><button type="button" className="sample-button" onClick={() => { setText(SAMPLE_RCA); setError(null); }}><Sparkles size={14} /> Try a sample RCA</button><span id="text-hint" className={text.length > 50_000 ? 'over-limit' : ''}>{text.length.toLocaleString()} / 50,000</span></div>
              </div>
            ) : (
              <div className="upload-area" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); selectFile(event.dataTransfer.files[0]); }}>
                <input ref={inputRef} type="file" id="source-file" accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf" onChange={handleFileChange} />
                {file ? <><span className="upload-icon"><FileText size={24} /></span><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(0)} KB · Ready to upload</span><button type="button" className="remove-file" onClick={() => { setFile(null); if (inputRef.current) inputRef.current.value = ''; }}><X size={14} /> Remove</button></> : <><span className="upload-icon"><UploadCloud size={25} /></span><strong>Drop your document here</strong><span>or <button type="button" className="browse-link" onClick={() => inputRef.current?.click()}>browse files</button> on your computer</span><small>.TXT, .MD, or text-based .PDF · Up to 10 MB</small></>}
              </div>
            )}
            {error && <p className="form-error" role="alert">{error}</p>}
            <div className="form-bottom"><span><span className="status-dot" /> Generates a private GitHub repository</span><button type="submit" className="primary-button" disabled={busy}>{busy ? 'Creating module…' : 'Create module'} <ArrowUpRight size={18} /></button></div>
          </form>
        </div>

        <aside className="process-panel" aria-label="What happens next">
          <div className="process-top"><span className="eyebrow">THE PROCESS</span><span className="process-number">/ 03</span></div>
          <h3>From context<br />to codebase.</h3>
          <div className="process-steps"><div><span>01</span><p><strong>Understand the work</strong><small>Extract one focused engineering task from your source.</small></p></div><div><span>02</span><p><strong>Build the exercise</strong><small>Create a runnable repository with a solvable bug or feature.</small></p></div><div><span>03</span><p><strong>Verify &amp; publish</strong><small>Check the task, shape two peer profiles, and publish privately.</small></p></div></div>
          <div className="process-note"><Sparkles size={17} /><span>Designed for a 30–60 minute learning sprint.</span></div>
        </aside>
      </div>
    </section>
  );
}
