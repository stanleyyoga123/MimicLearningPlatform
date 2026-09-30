import { ArrowRight, Lightbulb, MessageCircleMore } from 'lucide-react';
import { demoCohort, skillTopics } from '../demoCohort';

export function MentorInsights() {
  const checkIns = demoCohort.filter((learner) => learner.checkIn);
  return <div className="mentor-insights">
    <section className="mentor-panel" aria-labelledby="mentor-checkins-title"><div className="mentor-section-heading"><div><span className="eyebrow">NEXT CONVERSATIONS</span><h2 id="mentor-checkins-title">Where to step in</h2><p>Prompts for a focused mentor check-in.</p></div><MessageCircleMore size={20} aria-hidden="true" /></div><ol className="mentor-checkin-list">{checkIns.map((learner, index) => <li key={learner.name}><span className="mentor-checkin-number">0{index + 1}</span><div><strong>{learner.name}</strong><span>{learner.checkIn}</span></div><ArrowRight size={16} aria-hidden="true" /></li>)}</ol></section>
    <section className="mentor-panel mentor-coverage" aria-labelledby="mentor-coverage-title"><div className="mentor-section-heading"><div><span className="eyebrow">SKILL COVERAGE</span><h2 id="mentor-coverage-title">Cohort signals</h2><p>Average of these five sample skill indicators.</p></div><Lightbulb size={20} aria-hidden="true" /></div><div className="mentor-coverage-list">{skillTopics.map((topic) => { const average = Math.round(demoCohort.reduce((sum, learner) => sum + learner.skills[topic], 0) / demoCohort.length); return <div className="mentor-coverage-item" key={topic}><div><strong>{topic}</strong><span>{average}%</span></div><div className="mentor-coverage-track" role="img" aria-label={`${topic}: ${average} percent sample average`}><span style={{ width: `${average}%` }} /></div></div>; })}</div></section>
  </div>;
}
