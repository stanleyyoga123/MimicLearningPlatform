import { ArrowLeft, ArrowUpRight, Check, Github, LoaderCircle, MessageCircle, Send, X } from 'lucide-react';
import { useEffect, useRef, type FormEvent } from 'react';
import type { AvailableModule } from '../../modules/hooks/useAvailableModules';
import type { useWorkspaceSession } from '../hooks/useWorkspaceSession';
import { SubmissionPanel } from '../../submissions/components/SubmissionPanel';
import type { useSubmissions } from '../../submissions/hooks/useSubmissions';
import { ChatMarkdown } from './ChatMarkdown';

type TaskWorkspaceProps = {
  module: AvailableModule;
  workspace: ReturnType<typeof useWorkspaceSession>;
  submissions: ReturnType<typeof useSubmissions>;
};

export function TaskWorkspace({ module, workspace, submissions }: TaskWorkspaceProps) {
  const session = workspace.session;
  const activeAgent = session?.agents.find((agent) => agent.id === workspace.selectedAgentId);
  const messages = activeAgent ? workspace.transcripts[activeAgent.id] ?? [] : [];
  const pending = workspace.pendingTurn?.agentId === activeAgent?.id ? workspace.pendingTurn : null;
  const draft = activeAgent ? workspace.drafts[activeAgent.id] ?? '' : '';
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const list = messagesRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages.length, pending?.reply, pending?.question, activeAgent?.id]);

  const handleSend = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (activeAgent) void workspace.send(activeAgent.id);
  };

  return <section className="workspace-view">
    <div className="workspace-heading"><div><div className="hero-label"><span className="small-line" /> LEARNER WORKSPACE</div><h1>{module.spec.title}<span className="title-period">.</span></h1><p>Work through the assignment with the project team. Conversations end when you close this workspace.</p></div><button className="workspace-close" onClick={() => void workspace.close()}><X size={16} /> Close workspace</button></div>
    <div className="workspace-layout">
      <aside className="workspace-context">
        <div className="workspace-context-head"><span className="eyebrow">YOUR ASSIGNMENT</span><h2>What you’re building</h2><p>{module.spec.task_brief}</p></div>
        <div className="workspace-context-section"><h3>Acceptance criteria</h3><ul>{module.spec.acceptance_criteria.map((criterion) => <li key={criterion}><Check size={15} />{criterion}</li>)}</ul></div>
        <a className="workspace-repo" href={module.repository_url} target="_blank" rel="noopener noreferrer"><Github size={17} /> Open starter repository <ArrowUpRight size={15} /></a>
      </aside>

      <div className="workspace-chat">
        {!session ? <div className="workspace-session-state" role="status">
          {workspace.starting ? <><LoaderCircle size={31} className="spin" /><h2>Setting up your team…</h2><p>Preparing a conversation for this assignment.</p></> : workspace.ended ? <><MessageCircle size={31} /><h2>Conversation ended</h2><p>This session is closed. Start a new one to talk with the team again.</p><button className="primary-button" onClick={() => void workspace.start(module.id)}>Start a new session</button></> : <><MessageCircle size={31} /><h2>Could not start the conversation</h2><p role="alert">{workspace.error || 'Please try again.'}</p><button className="primary-button" onClick={() => void workspace.start(module.id)}>Try again</button></>}
        </div> : <>
          <div className="workspace-conversation-label"><span className="eyebrow">PROJECT TEAM</span><h2>Conversation</h2></div>
          <div className="workspace-agent-tabs" role="tablist" aria-label="Project team">{session.agents.map((agent) => <button key={agent.id} type="button" role="tab" aria-selected={agent.id === activeAgent?.id} className={agent.id === activeAgent?.id ? 'active' : ''} onClick={() => workspace.selectAgent(agent.id)}><span className="workspace-agent-avatar">{agent.name.slice(0, 1)}</span><span><strong>{agent.name}</strong><small>{agent.role}</small></span></button>)}</div>
          {activeAgent && <><div className="workspace-chat-heading"><span className="workspace-agent-avatar">{activeAgent.name.slice(0, 1)}</span><div><strong>{activeAgent.name}</strong><small>{activeAgent.description}</small></div></div>
            <div className="workspace-messages" ref={messagesRef} role="log" aria-label={`Conversation with ${activeAgent.name}`}>
              {messages.length === 0 && !pending && <div className="workspace-welcome"><MessageCircle size={24} /><h2>Ask {activeAgent.name}</h2><p>{activeAgent.description}</p><small>Share a question, code snippet, or error message. The team knows the generated starter, but cannot see changes on your computer.</small></div>}
              {messages.map((message, index) => <div className={`workspace-message ${message.role}`} key={`${index}-${message.role}`}><span>{message.role === 'learner' ? 'YOU' : activeAgent.name.toUpperCase()}</span><ChatMarkdown content={message.content} /></div>)}
              {pending && <><div className="workspace-message learner"><span>YOU</span><ChatMarkdown content={pending.question} /></div>{pending.reply && <div className="workspace-message assistant"><span>{activeAgent.name.toUpperCase()}</span><ChatMarkdown content={pending.reply} /></div>}</>}
              {workspace.busyAgentId === activeAgent.id && <div className="workspace-typing" role="status"><LoaderCircle size={15} className="spin" /> {pending?.reply ? `${activeAgent.name} is responding…` : `${activeAgent.name} is thinking…`}</div>}
            </div>
            <form className="workspace-composer" onSubmit={handleSend}><label htmlFor="workspace-message">Message {activeAgent.name}</label>{workspace.error && <p className="workspace-chat-error" role="alert">{workspace.error} Your message is still here; you can try again.</p>}<div className="workspace-compose-row"><textarea id="workspace-message" rows={3} maxLength={4000} value={draft} onChange={(event) => workspace.setDraft(activeAgent.id, event.target.value)} placeholder="Ask a question or paste code or an error…" disabled={workspace.busyAgentId !== null} /><button className="primary-button" type="submit" disabled={workspace.busyAgentId !== null || !draft.trim()}><Send size={16} /> Send message</button></div><small>Conversation is temporary · {draft.length}/4000 characters</small></form>
          </>}
        </>}
      </div>
    </div>
    <SubmissionPanel key={module.id} submissions={submissions} />
    <button className="back-link workspace-back" onClick={() => void workspace.close()}><ArrowLeft size={16} /> Back to assignment</button>
  </section>;
}
