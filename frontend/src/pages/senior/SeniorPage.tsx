import { SidebarToggle } from '../../features/sidebar/SidebarToggle';
import { useSidebarVisibility } from '../../features/sidebar/useSidebarVisibility';
import { ArrowLeft, ArrowRight, CircleHelp, FolderKanban, GraduationCap, Plus, RefreshCw, UsersRound } from 'lucide-react';
import { useModules } from '../../features/modules/hooks/useModules';
import { SubmissionForm } from '../../features/modules/components/SubmissionForm';
import { ModuleProgress } from '../../features/modules/components/ModuleProgress';
import { ModuleResult } from '../../features/modules/components/ModuleResult';
import type { ModuleApi } from '../../features/modules/services/ModuleApi';
import { useSeniorNameTooltip } from './useSeniorNameTooltip';

type SeniorPageProps = { api: ModuleApi };

function sidebarTitle(title: string): string {
  const characters = Array.from(title);
  return characters.length > 25 ? `${characters.slice(0, 25).join('')}...` : title;
}

export function SeniorPage({ api }: SeniorPageProps) {
  const sidebar = useSidebarVisibility();
  const modules = useModules(api);
  const nameTooltip = useSeniorNameTooltip();
  const current = modules.selected;
  const isNew = !modules.selectedId;
  return <div className="app-shell">
    <aside className="sidebar" id="mimic-sidebar" hidden={!sidebar.expanded}><button className="brand" onClick={() => modules.select(null)} aria-label="Mimic home"><span className="brand-symbol">m<span>.</span></span><span className="brand-name">Mimic<small>PRODUCTION PRACTICE</small></span></button>
      <div className="sidebar-main"><button className={`nav-item ${isNew ? 'selected' : ''}`} onClick={() => modules.select(null)}><span className="nav-icon"><Plus size={18} /></span> New module <ArrowRight size={15} className="nav-arrow" /></button><a className="nav-item" href="/mentor"><span className="nav-icon"><UsersRound size={18} /></span> Mentor dashboard</a><div className="nav-section-title"><span>YOUR WORKSPACE</span><span>{modules.items.length.toString().padStart(2, '0')}</span></div><div className="history-list">{modules.items.length === 0 && !modules.listError ? <p className="empty-history">Your modules will appear here.</p> : modules.items.map((item) => <button key={item.id} aria-label={item.title || 'Untitled module'} className={`history-item ${modules.selectedId === item.id ? 'selected' : ''}`} onMouseEnter={(event) => nameTooltip.show(event.currentTarget, item.title || 'Untitled module', 'right')} onFocus={(event) => nameTooltip.show(event.currentTarget, item.title || 'Untitled module', 'right')} onMouseLeave={nameTooltip.scheduleHide} onBlur={nameTooltip.scheduleHide} onClick={() => { nameTooltip.hide(); modules.select(item.id); }}><span className="history-icon"><FolderKanban size={16} /></span><span className="history-text"><strong>{sidebarTitle(item.title || 'Untitled module')}</strong><small><span className={`history-status ${item.status}`} />{item.status === 'completed' ? 'Ready' : item.status === 'failed' ? 'Needs attention' : 'In progress'} · {new Date(item.created_at).toLocaleDateString()}</small></span></button>)}</div>{modules.listError && <div className="sidebar-error" role="alert"><p>{modules.listError}</p><button onClick={() => void modules.refreshList()}><RefreshCw size={13} /> Try again</button></div>}</div>
      <div className="sidebar-bottom"><a className="role-switch" href="/junior"><GraduationCap size={17} /><span>View junior page</span><ArrowRight size={14} /></a><div className="sidebar-help"><CircleHelp size={18} /><span><strong>Built for learning by doing.</strong><small>Production scenarios. Practical skills.</small></span></div><span className="sidebar-version">MIMIC <span>·</span> MVP 01</span></div>
    </aside>
    <main className="main-area"><header className="topbar"><SidebarToggle expanded={sidebar.expanded} onToggle={sidebar.toggle} /><div className="breadcrumbs"><span>WORKSPACE</span><span className="crumb-separator">/</span><strong tabIndex={0} onMouseEnter={(event) => nameTooltip.show(event.currentTarget, isNew ? 'NEW MODULE' : current?.title || 'MODULE', 'bottom')} onFocus={(event) => nameTooltip.show(event.currentTarget, isNew ? 'NEW MODULE' : current?.title || 'MODULE', 'bottom')} onMouseLeave={nameTooltip.scheduleHide} onBlur={nameTooltip.scheduleHide}>{isNew ? 'NEW MODULE' : current?.title || 'MODULE'}</strong></div><div className="topbar-right"><span className="local-indicator"><i /> LOCAL STUDIO</span><span className="top-avatar">M</span></div></header><div className="content-area">{!isNew && <button className="back-link" onClick={() => modules.select(null)}><ArrowLeft size={16} /> Back to workspace</button>}{isNew ? <SubmissionForm busy={modules.busy} onSubmit={modules.create} /> : modules.loading && !current ? <div className="loading-detail">Loading module…</div> : modules.detailError && !current ? <div className="detail-error" role="alert"><p>{modules.detailError}</p><button onClick={() => modules.select(null)}>Return to workspace</button></div> : current?.status === 'completed' || current?.status === 'failed' ? <ModuleResult module={current} busy={modules.busy} onRetry={() => void modules.retry()} /> : current ? <ModuleProgress module={current} /> : null}{modules.detailError && current && <p className="inline-error" role="alert">{modules.detailError}</p>}</div><footer className="main-footer"><span>CRAFTED FOR THE CURIOUS</span><span>LEARN BY BUILDING <ArrowRight size={14} /></span></footer></main>
    {nameTooltip.tooltip}
  </div>;
}
