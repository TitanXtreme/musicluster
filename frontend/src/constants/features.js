export const FEATURES = [
  { id: 'popularity',       label: 'Popularity',       hint: '0 – 100',         min: 0,   max: 100,  step: 1    },
  { id: 'duration_ms',      label: 'Duration (ms)',    hint: '> 0',             min: 1,   max: null, step: 1000 },
  { id: 'explicit',         label: 'Explicit',         hint: '0 or 1',          min: 0,   max: 1,    step: 1    },
  { id: 'danceability',     label: 'Danceability',     hint: '0 – 1',           min: 0,   max: 1,    step: 0.01 },
  { id: 'energy',           label: 'Energy',           hint: '0 – 1',           min: 0,   max: 1,    step: 0.01 },
  { id: 'key',              label: 'Key',              hint: '0 – 11',          min: 0,   max: 11,   step: 1    },
  { id: 'loudness',         label: 'Loudness (dB)',    hint: '-60 – 5',         min: -60, max: 5,    step: 0.1  },
  { id: 'mode',             label: 'Mode',             hint: '0=minor 1=major', min: 0,   max: 1,    step: 1    },
  { id: 'speechiness',      label: 'Speechiness',      hint: '0 – 1',           min: 0,   max: 1,    step: 0.01 },
  { id: 'acousticness',     label: 'Acousticness',     hint: '0 – 1',           min: 0,   max: 1,    step: 0.01 },
  { id: 'instrumentalness', label: 'Instrumentalness', hint: '0 – 1',           min: 0,   max: 1,    step: 0.01 },
  { id: 'liveness',         label: 'Liveness',         hint: '0 – 1',           min: 0,   max: 1,    step: 0.01 },
  { id: 'valence',          label: 'Valence',          hint: '0 – 1',           min: 0,   max: 1,    step: 0.01 },
  { id: 'tempo',            label: 'Tempo (BPM)',      hint: '> 0',             min: 1,   max: 300,  step: 0.1  },
  { id: 'time_signature',   label: 'Time Signature',   hint: '1 – 7',           min: 1,   max: 7,    step: 1    },
]

export const CLUSTERS = [
  {
    id: 0,
    label: 'Hip-Hop / Party',
    emoji: '🎤',
    vibe: 'party',
    color: '#a855f7',
    glow: 'rgba(168,85,247,0.25)',
    border: 'rgba(168,85,247,0.4)',
    description: 'Energetic tracks with explicit lyrics and strong rhythmic speech. High danceability — built for the dancefloor.',
  },
  {
    id: 1,
    label: 'Workout / Upbeat Pop',
    emoji: '💪',
    vibe: 'workout',
    color: '#22d3ee',
    glow: 'rgba(34,211,238,0.25)',
    border: 'rgba(34,211,238,0.4)',
    description: 'High-energy, feel-good mainstream pop with positive valence. Perfect for the gym and commutes.',
  },
  {
    id: 2,
    label: 'Chill / Study / Acoustic',
    emoji: '📚',
    vibe: 'study',
    color: '#34d399',
    glow: 'rgba(52,211,153,0.25)',
    border: 'rgba(52,211,153,0.4)',
    description: 'Low-energy, highly acoustic tracks with calm moods. Ideal for focus, relaxation, or winding down.',
  },
]

export const SAMPLE_SONGS = [
  {
    name: "Drake – God's Plan",
    values: { popularity:98, duration_ms:198973, explicit:1, danceability:0.754, energy:0.449,
              key:2, loudness:-9.21, mode:1, speechiness:0.109, acousticness:0.0332,
              instrumentalness:0, liveness:0.552, valence:0.357, tempo:77.169, time_signature:4 },
  },
  {
    name: 'Ed Sheeran – Shape of You',
    values: { popularity:95, duration_ms:233712, explicit:0, danceability:0.825, energy:0.652,
              key:1, loudness:-3.183, mode:0, speechiness:0.0802, acousticness:0.581,
              instrumentalness:0, liveness:0.0931, valence:0.931, tempo:95.977, time_signature:4 },
  },
  {
    name: 'Bon Iver – Skinny Love',
    values: { popularity:72, duration_ms:193520, explicit:0, danceability:0.408, energy:0.153,
              key:9, loudness:-14.2, mode:1, speechiness:0.028, acousticness:0.942,
              instrumentalness:0.00103, liveness:0.117, valence:0.254, tempo:96.0, time_signature:3 },
  },
]
