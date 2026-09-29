import { ArrowUpRight, Check, CheckCircle2, ClipboardList, Code2, Github, RotateCcw, Users, X } from 'lucide-react';
import type { Module } from '../schemas/module';

type ModuleResultProps = { module: Module; busy: boolean; onRetry: () => void };

export function ModuleResult({ module, busy, onRetry }: ModuleResultProps) {
  if (module.status === 'failed') return <div className="detail-view"><div className="hero-label"><span className="small-line" /> GENERATION INTERRUPTED</div><h1>We hit a <em>snag.</em></h1><p className="detail-intro">The module is saved. Review the issue below and retry when you’re ready.</p><div className="failure-card"><span className="failure-icon"><X size={22} /></span><div><span className="eyebrow">FAILED AT {module.stage.toUpperCase()}</span><h2>{module.error || 'The module could not be completed.'}</h2><p>Your source and progress remain available for a retry.</p><button className="primary-button" disabled={busy} onClick={onRetry}><RotateCcw size={17} /> {busy ? 'Retrying…' : 'Retry generation'}</button></div></div></div>;

  const spec = module.spec;
  if (!spec) return null;
  return <div className="detail-view result-view">
    <div className="result-topline"><div className="hero-label"><span className="small-line" /> MODULE READY</div><span className="ready-pill"><Check size={13} /> VERIFIED EXERCISE</span></div>
    <h1>{spec.title}<span className="title-period">.</span></h1>
    <p className="detail-intro">{spec.scenario}</p>
    <div className="result-actions"><span className="tag"><Code2 size={14} /> BACKEND ENGINEERING</span><span className="tag">{spec.task_type.toUpperCase()}</span><span className="tag">30–60 MIN</span>{module.repository_url && <a className="primary-button repo-button" href={module.repository_url} target="_blank" rel="noopener noreferrer"><Github size={18} /> Open private repository <ArrowUpRight size={17} /></a>}</div>

    <div className="result-grid"><section className="result-card task-card"><div className="section-heading"><span className="section-icon"><ClipboardList size={19} /></span><div><span className="eyebrow">THE ASSIGNMENT</span><h2>Your task</h2></div></div><p className="task-brief">{spec.task_brief}</p><div className="divider" /><h3>Learning objective</h3><p>{spec.learning_objective}</p><div className="divider" /><h3>Expected behavior</h3><p>{spec.expected_behavior}</p><div className="divider" /><h3>Acceptance criteria</h3><ul className="criteria-list">{spec.acceptance_criteria.map((criterion) => <li key={criterion}><span><Check size={13} /></span>{criterion}</li>)}</ul></section>
    <div className="right-stack"><section className="result-card"><div className="section-heading"><span className="section-icon"><CheckCircle2 size={19} /></span><div><span className="eyebrow">QUALITY GATE</span><h2>Verified to learn</h2></div></div><p>{module.verification?.summary || 'Verification details are available with the generated project.'}</p>{module.verification && <div className="check-list">{module.verification.checks.map((check) => <div key={check.name} className="verification-check"><span className={check.passed ? 'check-pass' : 'check-fail'}>{check.passed ? <Check size={13} /> : <X size={13} />}</span><div><strong>{check.name}</strong><small>{check.detail}</small></div></div>)}</div>}</section>
    <section className="result-card"><div className="section-heading"><span className="section-icon"><Users size={19} /></span><div><span className="eyebrow">THE PROJECT TEAM</span><h2>Meet your peers</h2></div></div><p>Two fictional teammates bring context from their own corners of the project.</p><div className="peer-list">{module.peers.map((peer, index) => <div className="peer" key={peer.name}><span className={`peer-avatar avatar-${index}`}>{peer.name.slice(0, 1)}</span><div><strong>{peer.name}</strong><small>{peer.role}</small><p>{peer.contribution_history}</p><span className="peer-responsibilities">{peer.responsibilities.join(' · ')}</span><span className="peer-files">Knows: {peer.owned_files.join(', ')}</span></div></div>)}</div></section></div></div>
    {spec.simplifications.length > 0 && <div className="simplifications"><strong>Adapted for the workshop</strong><p>{spec.simplifications.join(' ')}</p></div>}
    {module.commit_sha && <p className="commit-note">Published commit · <code>{module.commit_sha.slice(0, 12)}</code></p>}
  </div>;
}
