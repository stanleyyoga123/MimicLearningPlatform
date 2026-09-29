import { ArrowUpRight, CheckCircle2, Target } from 'lucide-react';

type DevelopmentItem = { title: string; detail: string };
type ProfileDevelopmentCardProps = {
  strengths: readonly DevelopmentItem[];
  growthAreas: readonly DevelopmentItem[];
};

export function ProfileDevelopmentCard({ strengths, growthAreas }: ProfileDevelopmentCardProps) {
  return <section className="profile-development" aria-label="Sample strengths and growth areas">
    <div className="profile-card profile-development-card">
      <div className="profile-card-heading"><div><span className="eyebrow">WHAT'S GOING WELL</span><h2>Strengths</h2></div><CheckCircle2 size={22} aria-hidden="true" /></div>
      <ul>{strengths.map((item) => <li key={item.title}><span className="profile-list-marker" /><div><strong>{item.title}</strong><p>{item.detail}</p></div></li>)}</ul>
    </div>
    <div className="profile-card profile-development-card profile-growth-card">
      <div className="profile-card-heading"><div><span className="eyebrow">WHAT TO PRACTICE NEXT</span><h2>Growth areas</h2></div><Target size={22} aria-hidden="true" /></div>
      <ul>{growthAreas.map((item) => <li key={item.title}><span className="profile-list-marker" /><div><strong>{item.title}</strong><p>{item.detail}</p></div></li>)}</ul>
      <a href="/junior" className="profile-inline-link">Browse available assignments <ArrowUpRight size={16} aria-hidden="true" /></a>
    </div>
  </section>;
}
