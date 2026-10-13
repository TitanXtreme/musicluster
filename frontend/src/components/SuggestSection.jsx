import { useState, useCallback } from 'react'
import { MOOD_PRESETS, FEATURES, CLUSTER_COLORS } from '../constants/clusters'
import styles from './SuggestSection.module.css'

const API = 'http://localhost:8000'

/* ── Suggestion row ───────────────────────────────────────────────────── */
function SuggestionRow({ song, onMoreLikeThis }) {
  const color = CLUSTER_COLORS[song.cluster_id] ?? '#888'
  return (
    <div className={styles.row}>
      <div className={styles.rowLeft}>
        <div className={styles.rowDot} style={{ background: color }} />
        <div className={styles.rowInfo}>
          <div className={styles.rowTitle}>{song.track_name}</div>
          <div className={styles.rowArtist}>{song.artists} · <span className={styles.rowGenre}>{song.track_genre}</span></div>
          <div className={styles.rowWhy}>{song.why}</div>
        </div>
      </div>
      <div className={styles.rowRight}>
        <div className={styles.matchWrap}>
          <span className={`mono ${styles.matchPct}`}>{Math.round(song.match_pct)}%</span>
          <div className="match-bar-track" style={{ width: 80 }}>
            <div className="match-bar-fill" style={{ width: `${song.match_pct}%`, background: color }} />
          </div>
          <span className={styles.matchLabel}>match</span>
        </div>
        <button className={`btn btn-ghost ${styles.morBtn}`} onClick={() => onMoreLikeThis(song)}>
          More like this ↗
        </button>
      </div>
    </div>
  )
}

/* ── Results panel ─────────────────────────────────────────────────────── */
function ResultsPanel({ results, loading, error, onRefresh, onMoreLikeThis, diversity, onDiversityChange }) {
  if (loading) return (
    <div className="empty-state">
      <span className="spinner" style={{ width: 28, height: 28, borderTopColor: 'var(--accent)' }} />
      <p>Finding similar songs…</p>
    </div>
  )
  if (error) return <div className="error-banner">⚠ {error}</div>
  if (!results) return (
    <div className="empty-state">
      <span className="icon">🎵</span>
      <p>Pick a mood, search a song, or set the sliders above to get suggestions.</p>
    </div>
  )
  if (results.length === 0) return (
    <div className="empty-state">
      <span className="icon">🔍</span>
      <p>No matching songs found. Try adjusting your settings.</p>
    </div>
  )

  return (
    <div className={styles.results}>
      <div className={styles.resultsHeader}>
        <span className={styles.resultsCount}>{results.length} suggestions · audio similarity only</span>
        <div className={styles.controls}>
          <div className={styles.diversityWrap}>
            <label className={styles.diversityLabel}>
              Diversity <span className="mono">{Math.round(diversity * 100)}%</span>
            </label>
            <input type="range" min={0} max={1} step={0.1} value={diversity}
              onChange={e => onDiversityChange(parseFloat(e.target.value))}
              style={{ width: 100 }} />
          </div>
          <button className="btn btn-ghost" onClick={onRefresh} style={{ padding: '7px 14px', fontSize:'0.8rem' }}>
            ↺ Refresh
          </button>
        </div>
      </div>
      <div className={styles.rowList}>
        {results.map((s, i) => (
          <SuggestionRow key={s.track_id ?? i} song={s} onMoreLikeThis={onMoreLikeThis} />
        ))}
      </div>
    </div>
  )
}

/* ── By Mood tab ──────────────────────────────────────────────────────── */
function MoodTab({ onSuggest, loading }) {
  const [selected, setSelected] = useState(null)

  function pick(mood) {
    setSelected(mood.id)
    onSuggest(mood.features)
  }

  return (
    <div className={styles.tabContent}>
      <p className={styles.tabHint}>Select a mood — we'll find songs with matching audio profiles.</p>
      <div className={styles.moodGrid}>
        {MOOD_PRESETS.map(m => (
          <button
            key={m.id}
            className={`chip ${selected === m.id ? 'active' : ''} ${styles.moodChip}`}
            onClick={() => pick(m)}
            disabled={loading}
          >
            {m.icon} {m.label}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ── By Song tab ──────────────────────────────────────────────────────── */
function SongTab({ onSuggest, loading }) {
  const [query, setQuery]       = useState('')
  const [results, setResults]   = useState([])
  const [searching, setSearching] = useState(false)
  const [picked, setPicked]     = useState([])
  const [searchErr, setSearchErr] = useState('')

  async function search() {
    if (!query.trim()) return
    setSearching(true); setSearchErr('')
    try {
      const res = await fetch(`${API}/songs/search?q=${encodeURIComponent(query)}&limit=20`)
      if (!res.ok) throw new Error('Search failed')
      setResults(await res.json())
    } catch { setSearchErr('Search failed — is the server running?') }
    finally { setSearching(false) }
  }

  function togglePick(song) {
    setPicked(p => p.find(s => s.track_id === song.track_id)
      ? p.filter(s => s.track_id !== song.track_id)
      : p.length < 3 ? [...p, song] : p)
  }

  function suggest() {
    if (!picked.length) return
    const avg = {}
    FEATURES.forEach(f => {
      avg[f.id] = picked.reduce((s, p) => s + (p.features[f.id] ?? 0), 0) / picked.length
    })
    onSuggest(avg, picked.map(p => p.track_id))
  }

  const color = (id) => CLUSTER_COLORS[id] ?? '#888'

  return (
    <div className={styles.tabContent}>
      <p className={styles.tabHint}>Search for 1–3 songs. We'll average their audio profiles and suggest similar tracks.</p>

      <div className={styles.searchRow}>
        <input type="search" placeholder="Search by song name or artist…" value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()} />
        <button className="btn btn-primary" onClick={search} disabled={searching} style={{ flexShrink:0 }}>
          {searching ? <span className="spinner"/> : 'Search'}
        </button>
      </div>

      {searchErr && <div className="error-banner">{searchErr}</div>}

      {picked.length > 0 && (
        <div className={styles.pickedWrap}>
          <span className={styles.pickedLabel}>Selected ({picked.length}/3):</span>
          <div className={styles.pickedList}>
            {picked.map(s => (
              <span key={s.track_id} className={`chip active ${styles.pickedChip}`} onClick={() => togglePick(s)}>
                <span className="dot" style={{ background: color(s.cluster_id) }} />
                {s.track_name} – {s.artists} ×
              </span>
            ))}
          </div>
          <button className="btn btn-primary" onClick={suggest} disabled={loading} style={{ marginLeft:'auto' }}>
            {loading ? <span className="spinner"/> : 'Suggest'}
          </button>
        </div>
      )}

      {results.length > 0 && (
        <div className={styles.searchResults}>
          {results.map(s => {
            const isPicked = picked.some(p => p.track_id === s.track_id)
            return (
              <div key={s.track_id} className={`${styles.searchRow2} ${isPicked ? styles.searchRowActive : ''}`}
                onClick={() => togglePick(s)} role="button" tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && togglePick(s)}>
                <span className="dot" style={{ background: color(s.cluster_id) }} />
                <div>
                  <div className={styles.srTitle}>{s.track_name}</div>
                  <div className={styles.srSub}>{s.artists} · {s.track_genre}</div>
                </div>
                {isPicked && <span className={styles.checkmark}>✓</span>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

/* ── By Sliders tab ───────────────────────────────────────────────────── */
function SliderTab({ onSuggest, loading }) {
  const defaults = Object.fromEntries(FEATURES.map(f => [f.id, f.default ?? (f.min + f.max) / 2]))
  const [vals, setVals] = useState(defaults)

  function update(id, v) { setVals(p => ({ ...p, [id]: parseFloat(v) })) }

  return (
    <div className={styles.tabContent}>
      <p className={styles.tabHint}>Set the 15 audio features using sliders and find the closest songs in the dataset.</p>
      <div className={styles.sliderGrid}>
        {FEATURES.map(f => (
          <div key={f.id} className={styles.sliderRow}>
            <label className={styles.sliderLabel}>{f.label}</label>
            <div className={styles.sliderInner}>
              <input type="range" min={f.min ?? 0} max={f.max ?? 1} step={f.step}
                value={vals[f.id]} onChange={e => update(f.id, e.target.value)} />
              <span className={`mono ${styles.sliderVal}`}>{Number(vals[f.id]).toFixed(f.step < 1 ? 2 : 0)}</span>
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 20 }}>
        <button className="btn btn-primary" onClick={() => onSuggest(vals)} disabled={loading}>
          {loading ? <><span className="spinner"/> Finding…</> : 'Find Similar Songs'}
        </button>
      </div>
    </div>
  )
}

/* ── Main section ─────────────────────────────────────────────────────── */
export default function SuggestSection() {
  const [tab, setTab]           = useState('mood')
  const [results, setResults]   = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [diversity, setDiversity] = useState(0)
  const [lastReq, setLastReq]   = useState(null)

  const TABS = [
    { id: 'mood', label: '🎭 By Mood' },
    { id: 'song', label: '🔍 By Song' },
    { id: 'sliders', label: '🎚 By Sliders' },
  ]

  async function suggest(features, excludeIds = []) {
    setError(''); setLoading(true)
    const req = { features, count: 10, diversity, exclude_ids: excludeIds }
    setLastReq(req)
    try {
      const res = await fetch(`${API}/suggest`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      })
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Error') }
      setResults(await res.json())
    } catch (e) {
      setError(e.message.includes('fetch') ? 'API unreachable — is the server running on port 8000?' : e.message)
    } finally { setLoading(false) }
  }

  function refresh() { if (lastReq) suggest(lastReq.features, lastReq.exclude_ids) }

  function moreLikeThis(song) {
    const feat = song.features
    if (feat) suggest(feat, [song.track_id])
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.inner}>
        <p className="section-label">Suggest for me</p>
        <h2 className={styles.heading}>Find songs by sound, not taste</h2>
        <p className={styles.sub}>
          Suggestions are based on <strong>audio feature similarity</strong> only — not listening history.
          We don't know your taste; we know the music.
        </p>

        <div className={styles.layout}>
          <div className={styles.controls}>
            <div className="tab-strip">
              {TABS.map(t => (
                <button key={t.id} className={`tab-btn ${tab === t.id ? 'active' : ''}`}
                  onClick={() => { setTab(t.id); setResults(null) }}>
                  {t.label}
                </button>
              ))}
            </div>

            <div className={styles.panel}>
              {tab === 'mood'    && <MoodTab    onSuggest={suggest} loading={loading} />}
              {tab === 'song'    && <SongTab    onSuggest={suggest} loading={loading} />}
              {tab === 'sliders' && <SliderTab  onSuggest={suggest} loading={loading} />}
            </div>
          </div>

          <div className={styles.resultsWrap}>
            <ResultsPanel
              results={results} loading={loading} error={error}
              onRefresh={refresh} onMoreLikeThis={moreLikeThis}
              diversity={diversity} onDiversityChange={v => { setDiversity(v); if (lastReq) setTimeout(() => suggest(lastReq.features, lastReq.exclude_ids), 0) }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
