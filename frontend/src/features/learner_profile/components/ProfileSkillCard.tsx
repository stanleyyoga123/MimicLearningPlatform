import type { ProfileSkill } from '../demoProfile';

type ProfileSkillCardProps = { skills: readonly ProfileSkill[] };

export function ProfileSkillCard({ skills }: ProfileSkillCardProps) {
  return <section className="profile-card profile-skill-card" aria-labelledby="profile-skills-title">
    <div className="profile-card-heading"><div><span className="eyebrow">SKILL PROFILE</span><h2 id="profile-skills-title">Where you stand</h2></div><span className="profile-heading-aside">SAMPLE ASSESSMENT</span></div>
    <p className="profile-card-intro">Illustrative skill levels for a learner progressing through backend assignments.</p>
    <div className="profile-skill-list">{skills.map((skill) => <div className="profile-skill" key={skill.name}>
      <div className="profile-skill-label"><strong>{skill.name}</strong><span>{skill.note} · {skill.level}%</span></div>
      <div className="profile-skill-track" role="progressbar" aria-label={skill.name} aria-valuenow={skill.level} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${skill.level}%` }} /></div>
    </div>)}</div>
    <p className="profile-footnote">These sample levels illustrate a future skills view; they do not evaluate your work.</p>
  </section>;
}
