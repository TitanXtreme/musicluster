import { useState, useEffect, useRef, useCallback } from 'react'
import Header from './components/Header'
import Hero from './components/Hero'
import ClusterSection from './components/ClusterSection'
import PredictSection from './components/PredictSection'
import SuggestSection from './components/SuggestSection'
import Footer from './components/Footer'

export const API = 'http://localhost:8000'

export default function App() {
  const [theme, setTheme]   = useState('dark')
  const [stats, setStats]   = useState(null)
  const [activeNav, setActiveNav] = useState('home')

  const heroRef    = useRef(null)
  const clusterRef = useRef(null)
  const predictRef = useRef(null)
  const suggestRef = useRef(null)

  // apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  // load stats once
  useEffect(() => {
    fetch(`${API}/stats`).then(r => r.json()).then(setStats).catch(() => {})
  }, [])

  // nav scroll spy
  useEffect(() => {
    const refs = [
      { id: 'home',    ref: heroRef },
      { id: 'clusters',ref: clusterRef },
      { id: 'predict', ref: predictRef },
      { id: 'suggest', ref: suggestRef },
    ]
    const obs = new IntersectionObserver(
      entries => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            const found = refs.find(r => r.ref.current === e.target)
            if (found) setActiveNav(found.id)
          }
        })
      },
      { threshold: 0.3 }
    )
    refs.forEach(r => r.ref.current && obs.observe(r.ref.current))
    return () => obs.disconnect()
  }, [])

  const scrollTo = useCallback((ref) => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  return (
    <div style={{ display:'flex', flexDirection:'column', minHeight:'100vh' }}>
      <Header
        theme={theme}
        onThemeToggle={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
        activeNav={activeNav}
        onNav={(id) => {
          setActiveNav(id)
          const map = { home: heroRef, clusters: clusterRef, predict: predictRef, suggest: suggestRef }
          scrollTo(map[id])
        }}
      />
      <main style={{ flex: 1 }}>
        <section ref={heroRef}>
          <Hero stats={stats} />
        </section>
        <section ref={clusterRef} style={{ padding: '80px 0' }}>
          <ClusterSection />
        </section>
        <section ref={predictRef} style={{ padding: '40px 0 80px' }}>
          <PredictSection />
        </section>
        <section ref={suggestRef} style={{ padding: '40px 0 100px', background: 'var(--surface)' }}>
          <SuggestSection />
        </section>
      </main>
      <Footer />
    </div>
  )
}
