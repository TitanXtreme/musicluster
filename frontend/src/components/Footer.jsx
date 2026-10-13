import styles from './Footer.module.css'

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <span>SoundCluster · K-Means on 15 Spotify audio features</span>
        <span className={styles.note}>Suggestions are audio similarity only — not personalised recommendations.</span>
      </div>
    </footer>
  )
}
