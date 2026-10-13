import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { CLUSTERS } from '../constants/clusters'
import styles from './ClusterSection.module.css'

function ClusterCard({ cluster }) {
  return (
    <div className={styles.card} style={{ '--c': cluster.color }}>
      <div className={styles.cardTop}>
        <div className={styles.colorChip} style={{ background: cluster.color }} />
        <div>
          <div className={styles.cardLabel}>{cluster.label}</div>
          <div className={styles.cardId}>Cluster #{cluster.id}</div>
        </div>
      </div>
      <p className={styles.cardDesc}>{cluster.description}</p>
      <div className={styles.chartWrap}>
        <ResponsiveContainer width="100%" height={180}>
          <RadarChart data={cluster.radarData} margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
            <PolarGrid stroke="var(--border)" strokeOpacity={0.8} />
            <PolarAngleAxis
              dataKey="feat"
              tick={{ fill: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-body)' }}
            />
            <Radar
              dataKey="value"
              stroke={cluster.color}
              strokeWidth={1.5}
              fill={cluster.color}
              fillOpacity={0.15}
              dot={{ r: 2, fill: cluster.color }}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                fontSize: 12,
                color: 'var(--text)',
              }}
              formatter={(v) => [`${v}`, 'Score']}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default function ClusterSection() {
  return (
    <div className={styles.wrap}>
      <div className={styles.inner}>
        <p className="section-label">The 3 clusters</p>
        <h2 className={styles.heading}>Audio profiles at a glance</h2>
        <p className={styles.sub}>
          Each cluster groups songs by their acoustic fingerprint. Radar charts show relative
          scores across six key dimensions — hover for exact values.
        </p>
        <div className={styles.grid}>
          {CLUSTERS.map(c => <ClusterCard key={c.id} cluster={c} />)}
        </div>
      </div>
    </div>
  )
}
