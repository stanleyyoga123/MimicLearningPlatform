import { ArrowUpRight, Check, ClipboardCheck, LoaderCircle, RotateCcw } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import type { Submission } from '../schemas/submission';
import type { useSubmissions } from '../hooks/useSubmissions';

type SubmissionState = ReturnType<typeof useSubmissions>;
type SubmissionPanelProps = { submissions: SubmissionState };

function statusLabel(record: Submission): string {
  switch (record.status) {
    case 'queued': return 'Queued for review';
    case 'running': return `Reviewing · ${record.stage}`;
    case 'needs_review': return 'Need review';
    case 'success': return 'Success — code review approved';
    case 'failed': return 'Review failed';
    case 'outdated': return 'Outdated — resubmit';
  }
}

export function SubmissionPanel({ submissions }: SubmissionPanelProps) {
  const [prUrl, setPrUrl] = useState('');
  const latest = submissions.records[0];
  const active = submissions.records.some((record) => record.status === 'queued' || record.status === 'running');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (await submissions.submit(prUrl)) setPrUrl('');
  };

  return <section className="submission-panel" aria-labelledby="submission-heading">
    <div className="submission-heading"><span className="section-icon"><ClipboardCheck size={19} /></span><div><span className="eyebrow">YOUR PULL REQUEST</span><h2 id="submission-heading">Submission</h2></div></div>
    <p>When the GitHub App is installed, opening or updating a ready pull request against main starts a review automatically. You can also paste its URL to request a review manually.</p>
    <form className="submission-form" onSubmit={(event) => void handleSubmit(event)}>
      <label htmlFor="submission-pr-url">GitHub pull request URL</label>
      <div className="submission-form-row"><input id="submission-pr-url" type="url" required placeholder="https://github.com/owner/repo/pull/1" value={prUrl} onChange={(event) => setPrUrl(event.target.value)} disabled={!submissions.ready || submissions.busy || active} /><button className="primary-button" type="submit" disabled={!submissions.ready || submissions.busy || active || !prUrl.trim()}>{submissions.busy ? <LoaderCircle size={15} className="spin" /> : <Check size={15} />} Submit for review</button></div>
    </form>
    {submissions.error && <div className="submission-error" role="alert"><span>{submissions.error}</span><button type="button" onClick={submissions.refresh}>Refresh</button></div>}
    {submissions.loading && <p className="submission-loading" role="status">Loading submissions…</p>}
    {!submissions.loading && !latest && !submissions.error && <p className="submission-empty">No submissions yet. Your review and past results will appear here.</p>}
    {latest && <div className="submission-history"><h3>Review history</h3>{submissions.records.map((record) => <article className={`submission-record submission-${record.status}`} key={record.id}>
      <div className="submission-record-head"><strong>{statusLabel(record)}</strong><span>{new Date(record.created_at).toLocaleString()}</span></div>
      <a className="submission-pr-link" href={record.pr_url} target="_blank" rel="noopener noreferrer">#{record.pr_number} {record.pr_title} <ArrowUpRight size={14} /></a>
      <p className="submission-commit">Reviewed commit: <code>{record.head_sha}</code></p>
      {record.status === 'success' && <p className="submission-test-note">Tests were not run.</p>}
      {record.summary && <p className="submission-summary">{record.summary}</p>}
      {record.findings.length > 0 && <ul className="submission-findings">{record.findings.map((finding, index) => <li key={`${record.id}-${index}`}><span className={finding.blocking ? 'submission-blocking' : 'submission-optional'}>{finding.blocking ? 'Needs change' : 'Suggestion'} · {finding.severity}</span>{finding.path && <code>{finding.path}{finding.line ? `:${finding.line}` : ''}</code>}<p>{finding.body}</p></li>)}</ul>}
      {record.error && <p className="submission-record-error" role="alert">{record.error}</p>}
      <div className="submission-record-actions">{record.github_review_url && <a href={record.github_review_url} target="_blank" rel="noopener noreferrer">View GitHub review <ArrowUpRight size={14} /></a>}
        {(record.status === 'needs_review' || record.status === 'outdated') && <button type="button" onClick={() => void submissions.submit(record.pr_url)} disabled={!submissions.ready || submissions.busy || active}><RotateCcw size={14} /> Resubmit</button>}
        {record.status === 'failed' && <button type="button" onClick={() => void submissions.retry(record.id)} disabled={!submissions.ready || submissions.busy || active}><RotateCcw size={14} /> Retry review</button>}
      </div>
    </article>)}</div>}
  </section>;
}
