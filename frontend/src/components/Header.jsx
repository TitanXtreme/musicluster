import styles from './Header.module.css'

const NAV = [
  { id: 'home',     label: 'Home' },
  { id: 'clusters', label: 'Clusters' },
  { id: 'predict',  label: 'Predict' },
  { id: 'suggest',  label: 'Suggest for Me' },
]

export default function Header({ theme, onThemeToggle, activeNav, onNav }) {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <div className={styles.brand} onClick={() => onNav('home')} role="button" tabIndex={0}
          onKeyDown={e => e.key === 'Enter' && onNav('home')}>
          <div className={styles.logo}>SC</div>
          <span className={styles.name}>SoundCluster</span>
        </div>

        <nav className={styles.nav} aria-label="Main navigation">
          {NAV.map(n => (
            <button
              key={n.id}
              className={`${styles.navBtn} ${activeNav === n.id ? styles.navActive : ''}`}
              onClick={() => onNav(n.id)}
              aria-current={activeNav === n.id ? 'page' : undefined}
            >
              {n.label}
              {n.id === 'suggest' && <span className={styles.badge}>New</span>}
            </button>
          ))}
        </nav>

        <button
          className={styles.themeBtn}
          onClick={onThemeToggle}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>
    </header>
  )
}
