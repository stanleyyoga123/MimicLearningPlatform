import { ArrowUpRight, Clock3 } from 'lucide-react';

type Recommendation = { category: string; title: string; detail: string; duration: string };
type ProfileRecommendationsProps = { recommendations: readonly Recommendation[] };

export function ProfileRecommendations({ recommendations }: ProfileRecommendationsProps) {
  return <section className="profile-recommendations" aria-labelledby="profile-recommendations-title">
    <div className="profile-section-heading"><div><span className="eyebrow">UP NEXT</span><h2 id="profile-recommendations-title">Suggested practice</h2></div><span>EXAMPLE RECOMMENDATIONS</span></div>
    <div className="profile-recommendation-grid">{recommendations.map((item, index) => <article className="profile-recommendation" key={item.title}>
      <div className="profile-recommendation-top"><span>{item.category}</span><span>0{index + 1}</span></div>
      <h3>{item.title}</h3><p>{item.detail}</p>
      <div className="profile-recommendation-foot"><span><Clock3 size={14} aria-hidden="true" />{item.duration}</span><span>ILLUSTRATIVE TASK</span></div>
    </article>)}</div>
    <a href="/junior" className="profile-inline-link">See live available assignments <ArrowUpRight size={16} aria-hidden="true" /></a>
  </section>;
}
