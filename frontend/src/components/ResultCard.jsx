import { useEffect, useRef } from 'react'
import styles from './ResultCard.module.css'

export default function ResultCard({ data }) {
  const fillRef = useRef(null)

  // Confidence: inverse of distance, clamped 0-100
  const maxDist = 5
  const conf = Math.max(0, Math.min(100, (1 - data.distance_to_center / maxDist) * 100))
  const confPct = conf.toFixed(1)

  useEffect(() => {
    // Animate bar after mount
    const el = fillRef.current
    if (!el) return
    el.style.width = '0%'
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.width = `${confPct}%`
      })
    })
  }, [data, confPct])

  return (
    <div className={styles.card} style={{ '--result-color': data.color, '--result-border': data.color + '55' }}>
      <div className={styles.header}>
        <span className={styles.emoji}>{data.emoji}</span>
        <div className={styles.info}>
          <h2 className={styles.label}>{data.label}</h2>
          <p className={styles.clusterId}>Cluster #{data.cluster_id} · <span style={{ textTransform: 'capitalize' }}>{data.vibe}</span></p>
        </div>
      </div>

      <p className={styles.description}>{data.description}</p>

      <div className={styles.meta}>
        <MetaItem label="Cluster ID" value={`#${data.cluster_id}`} />
        <MetaItem label="Vibe" value={data.vibe} capitalize />
        <MetaItem label="Distance to Center" value={data.distance_to_center} />
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Cluster Fit</span>
          <span className={styles.metaValue}>{confPct}%</span>
          <div className={styles.bar}>
            <div
              ref={fillRef}
              className={styles.barFill}
              style={{ background: data.color }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function MetaItem({ label, value, capitalize }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={{ fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--muted)' }}>{label}</span>
      <span style={{ fontSize: '0.9rem', fontWeight: 700, textTransform: capitalize ? 'capitalize' : undefined }}>{value}</span>
    </div>
  )
}
