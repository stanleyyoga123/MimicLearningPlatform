import { ArrowUpRight, BookOpenCheck, UsersRound } from 'lucide-react';
import { demoCohort } from '../demoCohort';

export function MentorOverview() {
  const checkIns = demoCohort.filter((learner) => learner.checkIn).length;
  const completed = demoCohort.reduce((total, learner) => total + learner.completed, 0);
  const active = demoCohort.filter((learner) => learner.inProgress).length;

  return <section className="mentor-overview" aria-label="Sample cohort overview">
    <div className="mentor-metric mentor-metric-primary"><UsersRound size={19} aria-hidden="true" /><span>JUNIORS IN YOUR COHORT</span><strong>{String(demoCohort.length).padStart(2, '0')}</strong><small>Illustrative learner profiles</small></div>
    <div className="mentor-metric"><ArrowUpRight size={19} aria-hidden="true" /><span>CHECK-INS TO PRIORITIZE</span><strong>{String(checkIns).padStart(2, '0')}</strong><small>Suggested mentor conversations</small></div>
    <div className="mentor-metric"><BookOpenCheck size={19} aria-hidden="true" /><span>PRACTICE SNAPSHOT</span><strong>{completed}<i> / {active}</i></strong><small>Completed / in progress</small></div>
  </section>;
}
