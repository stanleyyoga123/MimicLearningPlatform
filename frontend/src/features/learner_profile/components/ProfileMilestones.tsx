type Milestone = { title: string; detail: string; date: string };
type ProfileMilestonesProps = { milestones: readonly Milestone[] };

export function ProfileMilestones({ milestones }: ProfileMilestonesProps) {
  return <section className="profile-card profile-milestones" aria-labelledby="profile-milestones-title">
    <div className="profile-card-heading"><div><span className="eyebrow">THE JOURNEY</span><h2 id="profile-milestones-title">Recent milestones</h2></div><span className="profile-heading-aside">SAMPLE TIMELINE</span></div>
    <ol>{milestones.map((item) => <li key={item.title}><span className="profile-milestone-dot" aria-hidden="true" /><div><strong>{item.title}</strong><p>{item.detail}</p></div><span className="profile-milestone-date">{item.date}</span></li>)}</ol>
  </section>;
}
