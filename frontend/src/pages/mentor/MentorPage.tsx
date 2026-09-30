import { SidebarToggle } from '../../features/sidebar/SidebarToggle';
import { useSidebarVisibility } from '../../features/sidebar/useSidebarVisibility';
import { ArrowRight, BookOpen, CircleHelp, FolderKanban, GraduationCap, UsersRound } from 'lucide-react';
import { MentorInsights } from '../../features/mentor_dashboard/components/MentorInsights';
import { MentorOverview } from '../../features/mentor_dashboard/components/MentorOverview';
import { MentorRoster } from '../../features/mentor_dashboard/components/MentorRoster';
import '../../features/mentor_dashboard/mentorDashboard.css';

export function MentorPage() {
  const sidebar = useSidebarVisibility();
  return <div className="app-shell mentor-page">
    <aside className="sidebar" id="mimic-sidebar" hidden={!sidebar.expanded}><a className="brand brand-link" href="/mentor" aria-label="Mimic mentor home"><span className="brand-symbol">m<span>.</span></span><span className="brand-name">Mimic<small>PRODUCTION PRACTICE</small></span></a><nav className="sidebar-main" aria-label="Mentor navigation"><a className="nav-item selected" href="/mentor" aria-current="page"><span className="nav-icon"><UsersRound size={18} /></span> Mentor dashboard <ArrowRight size={15} className="nav-arrow" /></a><div className="nav-section-title"><span>EXPLORE MIMIC</span><span>03 VIEWS</span></div><a className="nav-item" href="/senior"><span className="nav-icon"><FolderKanban size={18} /></span> Senior space</a><a className="nav-item" href="/junior"><span className="nav-icon"><BookOpen size={18} /></span> Junior space</a><p className="mentor-sidebar-copy">See where learners are growing, where they are stuck, and what might help next.</p></nav><div className="sidebar-bottom"><div className="sidebar-help"><CircleHelp size={18} /><span><strong>A mentor's view of practice.</strong><small>Illustrative cohort · static preview</small></span></div><span className="sidebar-version">MIMIC <span>·</span> MVP 01</span></div></aside>
    <main className="main-area"><header className="topbar"><SidebarToggle expanded={sidebar.expanded} onToggle={sidebar.toggle} /><div className="breadcrumbs"><span>MENTOR SPACE</span><span className="crumb-separator">/</span><strong>COHORT OVERVIEW</strong></div><div className="topbar-right"><span className="local-indicator"><i /> LOCAL STUDIO</span><span className="top-avatar" aria-label="Mentor demo account"><GraduationCap size={17} aria-hidden="true" /></span></div></header>
      <div className="content-area mentor-content"><div className="mentor-intro"><h1>Mentor dashboard</h1><span className="mentor-demo-badge">DEMO COHORT · SAMPLE DATA</span></div><MentorOverview /><MentorRoster /><MentorInsights /><p className="mentor-disclosure">This dashboard previews a future mentor experience using illustrative data. Learner levels, skill indicators, check-ins, and suggested tasks are not connected to live assignments or reviews.</p></div>
      <footer className="main-footer"><span>CRAFTED FOR THE CURIOUS</span><span>GUIDE THE NEXT STEP <ArrowRight size={14} /></span></footer></main>
  </div>;
}
