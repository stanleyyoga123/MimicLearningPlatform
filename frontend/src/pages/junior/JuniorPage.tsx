import { SidebarToggle } from '../../features/sidebar/SidebarToggle';
import { useSidebarVisibility } from '../../features/sidebar/useSidebarVisibility';
import { ArrowLeft, ArrowRight, ArrowUpRight, BookOpen, CircleHelp, FolderKanban, RefreshCw, UserRound, UsersRound } from 'lucide-react';
import { useEffect } from 'react';
import { demoProfile } from '../../features/learner_profile/demoProfile';
import { JuniorModuleDetail } from '../../features/modules/components/JuniorModuleDetail';
import { useAvailableModules } from '../../features/modules/hooks/useAvailableModules';
import type { ModuleApi } from '../../features/modules/services/ModuleApi';
import { TaskWorkspace } from '../../features/sessions/components/TaskWorkspace';
import { useWorkspaceSession } from '../../features/sessions/hooks/useWorkspaceSession';
import type { SessionApi } from '../../features/sessions/services/SessionApi';
import { useSubmissions } from '../../features/submissions/hooks/useSubmissions';
import type { SubmissionApi } from '../../features/submissions/services/SubmissionApi';

type JuniorPageProps = { api: ModuleApi; sessionApi: SessionApi; submissionApi: SubmissionApi };

export function JuniorPage({ api, sessionApi, submissionApi }: JuniorPageProps) {
  const sidebar = useSidebarVisibility();
  const modules = useAvailableModules(api);
  const workspace = useWorkspaceSession(sessionApi);
  const submissions = useSubmissions(submissionApi, modules.selected?.id ?? null);
  const workspaceModuleId = workspace.moduleId;
  const closeWorkspace = workspace.close;
  const showingCatalog = modules.selectedId === null;

  useEffect(() => {
    if (workspaceModuleId && workspaceModuleId !== modules.selectedId) void closeWorkspace();
  }, [modules.selectedId, workspaceModuleId, closeWorkspace]);

  const handleCatalog = () => {
    void workspace.close();
    modules.select(null);
  };

  const handleStart = () => {
    if (modules.selected) void workspace.start(modules.selected.id);
  };

  return <div className="app-shell junior-page">
    <aside className="sidebar" id="mimic-sidebar" hidden={!sidebar.expanded}>
      <a className="brand brand-link" href="/junior" aria-label="Mimic junior home"><span className="brand-symbol">m<span>.</span></span><span className="brand-name">Mimic<small>PRODUCTION PRACTICE</small></span></a>
      <div className="sidebar-main"><button className={`nav-item ${showingCatalog ? 'selected' : ''}`} onClick={handleCatalog}><span className="nav-icon"><BookOpen size={18} /></span> Available tasks <ArrowRight size={15} className="nav-arrow" /></button><a className="nav-item" href="/junior/profile"><span className="nav-icon"><UserRound size={18} /></span> My profile</a><div className="nav-section-title"><span>LEARNER SPACE</span><span>{modules.items.length.toString().padStart(2, '0')}</span></div><p className="junior-sidebar-copy">Pick a task, explore the starter code, and work through its acceptance criteria.</p></div>
      <div className="sidebar-bottom"><a className="role-switch" href="/mentor"><UsersRound size={17} /><span>View mentor dashboard</span><ArrowRight size={14} /></a><a className="role-switch" href="/senior"><FolderKanban size={17} /><span>View senior page</span><ArrowRight size={14} /></a><div className="sidebar-help"><CircleHelp size={18} /><span><strong>Built for learning by doing.</strong><small>Production scenarios. Practical skills.</small></span></div><span className="sidebar-version">MIMIC <span>·</span> MVP 01</span></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><SidebarToggle expanded={sidebar.expanded} onToggle={sidebar.toggle} /><div className="breadcrumbs"><span>LEARNER SPACE</span><span className="crumb-separator">/</span><strong>{showingCatalog ? 'AVAILABLE TASKS' : workspace.moduleId ? 'WORKSPACE' : modules.selected?.spec.title || 'ASSIGNMENT'}</strong></div><div className="topbar-right"><span className="local-indicator"><i /> LOCAL STUDIO</span><a className="top-avatar" href="/junior/profile" aria-label={`View ${demoProfile.name}'s learning profile`}>{demoProfile.initials.charAt(0)}</a></div></header>
      <div className="content-area">
        {showingCatalog ? <section className="junior-catalog">
          <div className="hero-label"><span className="small-line" /> THE LEARNER SPACE</div>
          <div className="junior-catalog-head"><div><h1>Find your next <em>challenge.</em></h1><p className="hero-copy">Real backend tasks, built from real project context. Choose an assignment and make the code your own.</p></div><span className="junior-catalog-count">{modules.items.length.toString().padStart(2, '0')}<small>AVAILABLE MODULES</small></span></div>
          <div className="junior-list-heading"><div><span className="eyebrow">THE TASK BOARD</span><h2>Available assignments</h2></div><button className="refresh-button" onClick={() => void modules.refresh()} disabled={modules.loading}><RefreshCw size={15} /> Refresh tasks</button></div>
          {modules.loading && modules.items.length === 0 ? <p className="junior-state" role="status">Loading available tasks…</p> : null}
          {modules.error && <div className="junior-state junior-error" role="alert"><p>{modules.error}</p><button className="primary-button" onClick={() => void modules.refresh()}>Try again</button></div>}
          {!modules.loading && !modules.error && modules.items.length === 0 && <div className="junior-state junior-empty"><BookOpen size={28} /><h3>No tasks available yet</h3><p>Completed modules with a published starter repository will appear here.</p></div>}
          {modules.items.length > 0 && <div className="junior-task-grid">{modules.items.map((item, index) => <article className="junior-task-card" key={item.id}><div className="junior-task-card-top"><span className="junior-card-number">{String(index + 1).padStart(2, '0')}</span><span className="ready-pill">READY TO START</span></div><div className="junior-task-card-body"><span className="eyebrow">BACKEND ENGINEERING · {item.spec.task_type.toUpperCase()}</span><h3><button onClick={() => modules.select(item.id)}>{item.spec.title}</button></h3><p>{item.spec.scenario}</p></div><div className="junior-task-card-foot"><span>30–60 MIN · {new Date(item.created_at).toLocaleDateString()}</span><button aria-label={`Open ${item.spec.title}`} onClick={() => modules.select(item.id)}>View task <ArrowUpRight size={16} /></button></div></article>)}</div>}
        </section> : modules.selected && workspace.moduleId === modules.selected.id
          ? <TaskWorkspace module={modules.selected} workspace={workspace} submissions={submissions} />
          : <><button className="back-link" onClick={handleCatalog}><ArrowLeft size={16} /> Back to available tasks</button>
            {modules.loading && modules.items.length === 0 ? <p className="junior-state" role="status">Loading assignment…</p>
              : modules.selected ? <JuniorModuleDetail module={modules.selected} onStart={handleStart} />
                : !modules.error && <div className="junior-state junior-empty"><BookOpen size={28} /><h1>This module is not available yet.</h1><p>Choose a published assignment from the task board.</p><button className="primary-button" onClick={handleCatalog}>Browse available tasks</button></div>}
            {modules.error && <div className="junior-state junior-error" role="alert"><p>{modules.error}</p><button className="primary-button" onClick={() => void modules.refresh()}>Try again</button></div>}
          </>}
      </div>
      <footer className="main-footer"><span>CRAFTED FOR THE CURIOUS</span><span>LEARN BY BUILDING <ArrowRight size={14} /></span></footer>
    </main>
  </div>;
}
