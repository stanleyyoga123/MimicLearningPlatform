import { Check, LoaderCircle } from 'lucide-react';
import type { Module } from '../schemas/module';

const STAGES = [
  { key: 'extracting', label: 'Reading your source', description: 'Finding the task and key context' },
  { key: 'specifying', label: 'Designing the exercise', description: 'Defining a focused learning objective' },
  { key: 'reference', label: 'Building the reference', description: 'Creating a working backend project' },
  { key: 'starter', label: 'Preparing the starter', description: 'Adding the learner challenge and tests' },
  { key: 'verifying', label: 'Running verification', description: 'Checking both versions of the codebase' },
  { key: 'peers', label: 'Introducing the team', description: 'Giving each peer a bounded role' },
  { key: 'publishing', label: 'Publishing privately', description: 'Pushing the starter to GitHub' },
] as const;

type ModuleProgressProps = { module: Module };

export function ModuleProgress({ module }: ModuleProgressProps) {
  const currentIndex = STAGES.findIndex((stage) => stage.key === module.stage);
  return <div className="detail-view progress-view">
    <div className="hero-label"><span className="small-line" /> MODULE IN PROGRESS</div>
    <div className="detail-heading"><div><h1>Making something<br /><em>worth solving.</em></h1><p>Your source is becoming a focused engineering exercise. You can leave this page and return anytime.</p></div><div className="progress-orb"><LoaderCircle size={33} className="spin" /></div></div>
    <div className="progress-card"><div className="progress-card-head"><span className="eyebrow">BUILD PROGRESS</span><span className="live-pill"><span /> LIVE</span></div><h2>{module.title || 'Your new module'}</h2><div className="stage-list">{STAGES.map((stage, index) => { const done = currentIndex > index; const active = currentIndex === index || (module.stage === 'queued' && index === 0); return <div className={`stage-item ${done ? 'done' : ''} ${active ? 'current' : ''}`} key={stage.key}><span className="stage-indicator">{done ? <Check size={16} /> : active ? <LoaderCircle size={16} className="spin" /> : String(index + 1).padStart(2, '0')}</span><div><strong>{stage.label}</strong><small>{stage.description}</small></div>{active && <span className="stage-active-label">IN PROGRESS</span>}</div>; })}</div></div>
  </div>;
}
