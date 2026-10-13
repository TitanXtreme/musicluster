import { useState, useCallback } from 'react'
import { FEATURES, SAMPLE_SONGS } from '../constants/features'
import FeatureInput from './FeatureInput'
import styles from './PredictForm.module.css'

export default function PredictForm({ onPredict, loading, error }) {
  const [values, setValues]   = useState({})
  const [errors, setErrors]   = useState({})
  const [sampleIdx, setSampleIdx] = useState(0)

  const handleChange = useCallback((id, val) => {
    setValues(v => ({ ...v, [id]: val }))
    setErrors(e => ({ ...e, [id]: false }))
  }, [])

  function handleSample() {
    const s = SAMPLE_SONGS[sampleIdx % SAMPLE_SONGS.length]
    setSampleIdx(i => i + 1)
    setValues(s.values)
    setErrors({})
  }

  function handleClear() {
    setValues({})
    setErrors({})
  }

  function handleSubmit(e) {
    e.preventDefault()
    const newErrors = {}
    const body = {}
    let valid = true

    FEATURES.forEach(f => {
      const raw = values[f.id]
      const num = parseFloat(raw)
      if (raw === undefined || raw === '' || isNaN(num)) {
        newErrors[f.id] = true
        valid = false
      } else {
        body[f.id] = num
      }
    })

    setErrors(newErrors)
    if (valid) onPredict(body)
  }

  const currentSample = SAMPLE_SONGS[(sampleIdx) % SAMPLE_SONGS.length]

  return (
    <section>
      <p className={styles.sectionTitle}>Enter Song Features</p>
      <div className={styles.card}>
        <form onSubmit={handleSubmit} noValidate>
          <div className={styles.grid}>
            {FEATURES.map(f => (
              <FeatureInput
                key={f.id}
                feature={f}
                value={values[f.id] ?? ''}
                hasError={!!errors[f.id]}
                onChange={handleChange}
              />
            ))}
          </div>

          {error && (
            <div className={styles.errorBanner}>
              ⚠ {error}
            </div>
          )}

          <div className={styles.actions}>
            <button type="submit" className={styles.btnPredict} disabled={loading}>
              {loading ? <><span className={styles.spinner} /> Predicting…</> : 'Predict Cluster'}
            </button>
            <button type="button" className={styles.btnSample} onClick={handleSample}>
              Load Sample — {currentSample.name}
            </button>
            <button type="button" className={styles.btnClear} onClick={handleClear}>
              Clear
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}
