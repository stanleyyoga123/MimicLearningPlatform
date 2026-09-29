import { ArrowRight, BookOpen, CircleHelp, FolderKanban, UserRound } from 'lucide-react';
import { ProfileActivityCard } from '../../features/learner_profile/components/ProfileActivityCard';
import { ProfileDevelopmentCard } from '../../features/learner_profile/components/ProfileDevelopmentCard';
import { ProfileMetrics } from '../../features/learner_profile/components/ProfileMetrics';
import { ProfileMilestones } from '../../features/learner_profile/components/ProfileMilestones';
import { ProfileRecommendations } from '../../features/learner_profile/components/ProfileRecommendations';
import { ProfileSkillCard } from '../../features/learner_profile/components/ProfileSkillCard';
import { demoProfile } from '../../features/learner_profile/demoProfile';
import '../../features/learner_profile/learnerProfile.css';

export function JuniorProfilePage() {
  return <div className="app-shell junior-page profile-page">
    <aside className="sidebar">
      <a className="brand brand-link" href="/junior" aria-label="Mimic junior home"><span className="brand-symbol">m<span>.</span></span><span className="brand-name">Mimic<small>PRODUCTION PRACTICE</small></span></a>
      <nav className="sidebar-main" aria-label="Learner navigation">
        <a className="nav-item" href="/junior"><span className="nav-icon"><BookOpen size={18} /></span> Available tasks <ArrowRight size={15} className="nav-arrow" /></a>
        <a className="nav-item selected" href="/junior/profile" aria-current="page"><span className="nav-icon"><UserRound size={18} /></span> My profile <ArrowRight size={15} className="nav-arrow" /></a>
        <div className="nav-section-title"><span>LEARNER SPACE</span><span>PREVIEW</span></div>
        <p className="junior-sidebar-copy">A glimpse of how your practice, strengths, and next steps could come together.</p>
      </nav>
      <div className="sidebar-bottom"><a className="role-switch" href="/senior"><FolderKanban size={17} /><span>View senior page</span><ArrowRight size={14} /></a><div className="sidebar-help"><CircleHelp size={18} /><span><strong>Built for learning by doing.</strong><small>Production scenarios. Practical skills.</small></span></div><span className="sidebar-version">MIMIC <span>·</span> MVP 01</span></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="breadcrumbs"><span>LEARNER SPACE</span><span className="crumb-separator">/</span><strong>MY PROFILE</strong></div><div className="topbar-right"><span className="local-indicator"><i /> LOCAL STUDIO</span><span className="top-avatar" aria-label={`Sample learner ${demoProfile.name}`}>{demoProfile.initials.charAt(0)}</span></div></header>
      <div className="content-area profile-content">
        <div className="profile-intro"><div><div className="hero-label"><span className="small-line" /> LEARNER PROFILE</div><h1>Your practice, <em>in perspective.</em></h1><p>See how production style assignments could shape a clear picture of your progress and what to practice next.</p></div><span className="profile-demo-badge">DEMO PROFILE · SAMPLE DATA</span></div>
        <section className="profile-identity" aria-labelledby="profile-identity-title"><div className="profile-identity-avatar" aria-hidden="true">{demoProfile.initials}</div><div className="profile-identity-copy"><span className="eyebrow">SAMPLE LEARNER</span><h2 id="profile-identity-title">{demoProfile.name}</h2><p>{demoProfile.track} <span aria-hidden="true">·</span> {demoProfile.level}</p></div><div className="profile-identity-track"><span>LEARNING TRACK</span><strong>Backend engineering</strong><small>Practice with production scenarios</small></div></section>
        <ProfileMetrics metrics={demoProfile.metrics} />
        <div className="profile-main-grid"><ProfileSkillCard skills={demoProfile.skills} /><ProfileActivityCard activity={demoProfile.activity} /></div>
        <ProfileDevelopmentCard strengths={demoProfile.strengths} growthAreas={demoProfile.growthAreas} />
        <div className="profile-lower-grid"><ProfileRecommendations recommendations={demoProfile.recommendations} /><ProfileMilestones milestones={demoProfile.milestones} /></div>
        <p className="profile-disclosure">This page uses illustrative data to preview a future learner dashboard. Assignment availability and review results are not connected to this profile yet.</p>
      </div>
      <footer className="main-footer"><span>CRAFTED FOR THE CURIOUS</span><span>LEARN BY BUILDING <ArrowRight size={14} /></span></footer>
    </main>
  </div>;
}
