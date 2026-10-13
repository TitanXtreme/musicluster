import { useEffect, useRef, useState } from 'react'
import styles from './Hero.module.css'

function Counter({ end, duration = 1800, suffix = '' }) {
  const [val, setVal] = useState(0)
  const rafRef = useRef(null)

  useEffect(() => {
    if (!end) return
    const start = performance.now()
    const step = (now) => {
      const p = Math.min((now - start) / duration, 1)
      const ease = 1 - Math.pow(1 - p, 3) // ease-out-cubic
      setVal(Math.floor(ease * end))
      if (p < 1) rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current)
  }, [end, duration])

  return (
    <span className={`mono ${styles.counterNum}`}>
      {val.toLocaleString()}{suffix}
    </span>
  )
}

export default function Hero({ stats }) {
  return (
    <div className={styles.hero}>
      <div className={styles.inner}>
        <div className={styles.eyebrow}>Audio-feature clustering · K-Means</div>
        <h1 className={styles.heading}>
          Discover the shape<br />
          <span className={styles.accent}>of your music.</span>
        </h1>
        <p className={styles.sub}>
          We analyse 15 Spotify audio features to cluster songs by sound profile.
          No taste data, no streaming history — pure audio similarity.
        </p>

        <div className={styles.stats}>
          <div className={styles.statItem}>
            <Counter end={stats?.total_songs ?? 114000} suffix="" />
            <span className={styles.statLabel}>songs analysed</span>
          </div>
          <div className={styles.divider} />
          <div className={styles.statItem}>
            <Counter end={stats?.total_clusters ?? 3} duration={600} />
            <span className={styles.statLabel}>clusters</span>
          </div>
          <div className={styles.divider} />
          <div className={styles.statItem}>
            <Counter end={stats?.features_count ?? 15} duration={800} />
            <span className={styles.statLabel}>audio features</span>
          </div>
        </div>

        <div className={styles.clusterPills}>
          {['Hip-Hop / Party', 'Workout / Upbeat', 'Chill / Study'].map((l, i) => {
            const colors = ['#2a78d6', '#eb6834', '#1baf7a']
            return (
              <span key={i} className={styles.pill}>
                <span className="dot" style={{ background: colors[i] }} />
                {l}
              </span>
            )
          })}
        </div>
      </div>

      <div className={styles.glow} aria-hidden />
    </div>
  )
}
