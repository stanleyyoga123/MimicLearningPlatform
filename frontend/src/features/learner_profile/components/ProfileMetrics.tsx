import type { ProfileMetric } from '../demoProfile';

type ProfileMetricsProps = { metrics: readonly ProfileMetric[] };

export function ProfileMetrics({ metrics }: ProfileMetricsProps) {
  return <section className="profile-metrics" aria-label="Sample learning overview">
    {metrics.map((metric, index) => <article className="profile-metric" key={metric.label}>
      <span className="profile-metric-index">0{index + 1} / OVERVIEW</span>
      <strong>{metric.value}</strong>
      <span className="profile-metric-label">{metric.label}</span>
      <small>{metric.detail}</small>
    </article>)}
  </section>;
}
