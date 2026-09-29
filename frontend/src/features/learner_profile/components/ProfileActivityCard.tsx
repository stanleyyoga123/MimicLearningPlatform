import type { ProfileActivity } from '../demoProfile';

type ProfileActivityCardProps = { activity: readonly ProfileActivity[] };

export function ProfileActivityCard({ activity }: ProfileActivityCardProps) {
  const totalMinutes = activity.reduce((total, day) => total + day.minutes, 0);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const maxMinutes = Math.max(...activity.map((day) => day.minutes));

  return <section className="profile-card profile-activity-card" aria-labelledby="profile-activity-title">
    <div className="profile-card-heading"><div><span className="eyebrow">YOUR RHYTHM</span><h2 id="profile-activity-title">A week of practice</h2></div><span className="profile-heading-aside">SAMPLE WEEK</span></div>
    <div className="profile-activity-summary"><strong>{hours}h {minutes}m</strong><span>of focused learning this week</span></div>
    <div className="profile-activity-chart" role="img" aria-label={`Sample learning time this week: ${activity.map((day) => `${day.day} ${day.minutes} minutes`).join(', ')}`}>
      {activity.map((day) => <div className="profile-activity-day" key={day.day} aria-hidden="true"><div className="profile-activity-column"><span style={{ height: `${maxMinutes ? day.minutes / maxMinutes * 100 : 0}%` }} /></div><span>{day.day}</span><small>{day.minutes}m</small></div>)}
    </div>
  </section>;
}
