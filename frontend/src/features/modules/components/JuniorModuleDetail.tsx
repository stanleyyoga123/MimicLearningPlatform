import { ArrowRight, ArrowUpRight, Check, ClipboardList, Code2, Github, Users } from 'lucide-react';
import type { AvailableModule } from '../hooks/useAvailableModules';
import { SubmissionPanel } from '../../submissions/components/SubmissionPanel';
import type { useSubmissions } from '../../submissions/hooks/useSubmissions';

type JuniorModuleDetailProps = { module: AvailableModule; onStart: () => void; submissions: ReturnType<typeof useSubmissions> };

export function JuniorModuleDetail({ module, onStart, submissions }: JuniorModuleDetailProps) {
  const { spec } = module;

  return <article className="detail-view result-view junior-detail">
    <div className="hero-label"><span className="small-line" /> YOUR ASSIGNMENT</div>
    <h1>{spec.title}<span className="title-period">.</span></h1>
    <p className="detail-intro">{spec.scenario}</p>
    <div className="result-actions">
      <span className="tag"><Code2 size={14} /> BACKEND ENGINEERING</span>
      <span className="tag">{spec.task_type.toUpperCase()}</span>
      <span className="tag">30–60 MIN</span>
      <button className="primary-button junior-start-button" onClick={onStart}>Start task <ArrowRight size={17} /></button>
      <a className="junior-repo-link" href={module.repository_url} target="_blank" rel="noopener noreferrer"><Github size={18} /> Open starter repository <ArrowUpRight size={17} /></a>
    </div>

    <div className="result-grid">
      <section className="result-card task-card" aria-labelledby="junior-task-heading">
        <div className="section-heading"><span className="section-icon"><ClipboardList size={19} /></span><div><span className="eyebrow">THE ASSIGNMENT</span><h2 id="junior-task-heading">Your task</h2></div></div>
        <p className="task-brief">{spec.task_brief}</p>
        <div className="divider" /><h3>Learning objective</h3><p>{spec.learning_objective}</p>
        <div className="divider" /><h3>Expected behavior</h3><p>{spec.expected_behavior}</p>
        <div className="divider" /><h3>Acceptance criteria</h3>
        <ul className="criteria-list">{spec.acceptance_criteria.map((criterion) => <li key={criterion}><span><Check size={13} /></span>{criterion}</li>)}</ul>
      </section>

      <div className="right-stack">
        <section className="result-card junior-start-card"><span className="eyebrow">GETTING STARTED</span><h2>Build your solution</h2><p>Open the private starter repository, follow its README, and run the exercise tests as you work.</p><a href={module.repository_url} target="_blank" rel="noopener noreferrer">View repository <ArrowUpRight size={15} /></a></section>
        <section className="result-card" aria-labelledby="junior-peers-heading">
          <div className="section-heading"><span className="section-icon"><Users size={19} /></span><div><span className="eyebrow">THE PROJECT TEAM</span><h2 id="junior-peers-heading">Meet your peers</h2></div></div>
          <p>These fictional teammates know specific parts of the project.</p>
          <div className="peer-list">{module.peers.map((peer, index) => <div className="peer" key={peer.name}><span className={`peer-avatar avatar-${index}`}>{peer.name.slice(0, 1)}</span><div><strong>{peer.name}</strong><small>{peer.role}</small><p>{peer.contribution_history}</p><span className="peer-responsibilities">{peer.responsibilities.join(' · ')}</span><span className="peer-files">Their area: {peer.owned_files.join(', ')}</span></div></div>)}</div>
        </section>
      </div>
    </div>
    <SubmissionPanel key={module.id} submissions={submissions} />
    {spec.simplifications.length > 0 && <div className="simplifications"><strong>Adapted for the workshop</strong><p>{spec.simplifications.join(' ')}</p></div>}
  </article>;
}
