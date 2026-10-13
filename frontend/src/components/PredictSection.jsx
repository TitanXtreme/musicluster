import { useState, useCallback } from 'react'
import { FEATURES, SAMPLE_SONGS } from '../constants/clusters'
import { CLUSTER_COLORS } from '../constants/clusters'
import styles from './PredictSection.module.css'

const API = 'http://localhost:8000'

function FeatureField({ feat, value, hasError, onChange }) {
  return (
    <div className={styles.field}>
      <label htmlFor={feat.id} className={styles.label} title={feat.hint}>{feat.label}</label>
      <input
        id={feat.id}
        type="number"
        className={hasError ? 'error' : ''}
        value={value}
        min={feat.min ?? undefined}
        max={feat.max ?? undefined}
        step={feat.step}
        placeholder={feat.hint}
        onChange={e => onChange(feat.id, e.target.value)}
      />
      <span className={styles.hint}>{feat.hint}</span>
    </div>
  )
}

function ResultCard({ data }) {
  const color = CLUSTER_COLORS[data.cluster_id] ?? data.color
  const maxDist = 5
  const conf = Math.max(0, Math.min(100, (1 - data.distance_to_center / maxDist) * 100))

  return (
    <div className={`${styles.resultCard} anim-fade-up`} style={{ '--rc': color }}>
      <div className={styles.rcHeader}>
        <div className={styles.rcChip} style={{ background: color }} />
        <div>
          <div className={styles.rcLabel}>{data.label}</div>
          <div className={styles.rcMeta}>Cluster #{data.cluster_id} · audio similarity</div>
        </div>
        <div className={styles.rcConf}>
          <span className={`mono ${styles.rcPct}`}>{conf.toFixed(1)}%</span>
          <div className={styles.rcBarTrack}>
            <div className={styles.rcBarFill} style={{ width: `${conf}%`, background: color }} />
          </div>
          <span className={styles.rcConfLabel}>cluster fit</span>
        </div>
      </div>
      <p className={styles.rcDesc}>{data.description}</p>
      <div className={styles.rcStats}>
        <div><span className={styles.statKey}>Distance to centroid</span><span className={`mono ${styles.statVal}`}>{data.distance_to_center}</span></div>
        <div><span className={styles.statKey}>Vibe</span><span className={styles.statVal} style={{ textTransform:'capitalize' }}>{data.vibe}</span></div>
      </div>
    </div>
  )
}

export default function PredictSection() {
  const [values, setValues]   = useState({})
  const [fieldErrors, setFieldErrors] = useState({})
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)
  const [sampleIdx, setSampleIdx] = useState(0)

  const handleChange = useCallback((id, val) => {
    setValues(v => ({ ...v, [id]: val }))
    setFieldErrors(e => ({ ...e, [id]: false }))
  }, [])

  function loadSample() {
    const s = SAMPLE_SONGS[sampleIdx % SAMPLE_SONGS.length]
    setSampleIdx(i => i + 1)
    setValues(s.values)
    setFieldErrors({})
    setResult(null)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const errs = {}
    const body = {}
    let ok = true
    FEATURES.forEach(f => {
      const v = parseFloat(values[f.id])
      if (values[f.id] === undefined || values[f.id] === '' || isNaN(v)) {
        errs[f.id] = true; ok = false
      } else { body[f.id] = v }
    })
    setFieldErrors(errs)
    if (!ok) return

    setError(''); setResult(null); setLoading(true)
    try {
      const res = await fetch(`${API}/predict`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Error') }
      setResult(await res.json())
    } catch (e) {
      setError(e.message.includes('fetch') ? 'API unreachable — is the server running?' : e.message)
    } finally { setLoading(false) }
  }

  const nextSample = SAMPLE_SONGS[sampleIdx % SAMPLE_SONGS.length]

  return (
    <div className={styles.wrap}>
      <div className={styles.inner}>
        <p className="section-label">Cluster predictor</p>
        <h2 className={styles.heading}>What cluster is this song?</h2>
        <p className={styles.sub}>Enter the Spotify audio features for any track and we'll assign it to the nearest cluster.</p>

        <div className={styles.card}>
          <form onSubmit={handleSubmit} noValidate>
            <div className={styles.grid}>
              {FEATURES.map(f => (
                <FeatureField
                  key={f.id} feat={f}
                  value={values[f.id] ?? ''}
                  hasError={!!fieldErrors[f.id]}
                  onChange={handleChange}
                />
              ))}
            </div>

            {error && <div className="error-banner" style={{ marginBottom: 16 }}>⚠ {error}</div>}

            <div className={styles.actions}>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? <><span className="spinner" /> Predicting…</> : 'Predict Cluster'}
              </button>
              <button type="button" className="btn btn-ghost" onClick={loadSample}>
                Load sample — {nextSample.name}
              </button>
              <button type="button" className="btn btn-outline" onClick={() => { setValues({}); setFieldErrors({}); setResult(null) }}>
                Clear
              </button>
            </div>
          </form>
        </div>

        {result && <ResultCard data={result} />}
      </div>
    </div>
  )
}
