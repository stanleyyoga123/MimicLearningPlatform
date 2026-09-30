import { Clock3 } from 'lucide-react';
import { demoCohort, weakestTopic } from '../demoCohort';

export function MentorRoster() {
  return <section className="mentor-panel mentor-roster" aria-labelledby="mentor-roster-title">
    <div className="mentor-section-heading"><div><span className="eyebrow">THE COHORT</span><h2 id="mentor-roster-title">Your juniors</h2><p>Where each learner is now, and one practical next step.</p></div><span className="mentor-heading-count">{String(demoCohort.length).padStart(2, '0')} PEOPLE</span></div>
    <div className="mentor-roster-head" aria-hidden="true"><span>LEARNER / LEVEL</span><span>FOCUS AREA</span><span>SUGGESTED PRACTICE</span></div>
    <div className="mentor-roster-list">{demoCohort.map((learner) => <article className="mentor-learner" key={learner.name}>
      <div className="mentor-learner-identity"><span className="mentor-learner-avatar" aria-hidden="true">{learner.initials}</span><div><h3>{learner.name}</h3><span>{learner.level}</span><span className={`mentor-status mentor-status-${learner.status === 'Needs a nudge' ? 'attention' : learner.status === 'On track' ? 'progress' : 'stretch'}`}>{learner.status}</span></div></div>
      <div className="mentor-learner-focus"><small>WEAKEST TOPIC</small><strong>{weakestTopic(learner)}</strong><span>{learner.skills[weakestTopic(learner)]}% sample indicator</span></div>
      <div className="mentor-learner-task"><small>SUGGESTED TASK</small><strong>{learner.suggestedTask}</strong><p>{learner.taskReason}</p><span><Clock3 size={13} aria-hidden="true" /> {learner.taskDuration}</span></div>
    </article>)}</div>
  </section>;
}
