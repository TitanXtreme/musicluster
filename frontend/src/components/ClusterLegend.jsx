import styles from './ClusterLegend.module.css'
import { CLUSTERS } from '../constants/features'

export default function ClusterLegend() {
  return (
    <section>
      <p className={styles.sectionTitle}>Mood Clusters</p>
      <div className={styles.grid}>
        {CLUSTERS.map(c => (
          <div
            key={c.id}
            className={styles.card}
            style={{ '--c-border': c.border, '--c-glow': c.glow }}
          >
            <span className={styles.emoji}>{c.emoji}</span>
            <span className={styles.label} style={{ color: c.color }}>{c.label}</span>
            <span className={styles.desc}>{c.description}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
