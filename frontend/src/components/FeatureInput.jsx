import styles from './FeatureInput.module.css'

export default function FeatureInput({ feature, value, hasError, onChange }) {
  const { id, label, hint, min, max, step } = feature

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label} title={hint}>
        {label}
      </label>
      <input
        id={id}
        type="number"
        className={`${styles.input} ${hasError ? styles.inputError : ''}`}
        value={value}
        min={min ?? undefined}
        max={max ?? undefined}
        step={step}
        placeholder={hint}
        onChange={e => onChange(id, e.target.value)}
      />
      <span className={styles.hint}>{hint}</span>
    </div>
  )
}
