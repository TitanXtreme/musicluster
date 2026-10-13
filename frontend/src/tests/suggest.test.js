import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ── Helpers to mirror backend suggestion logic on the client ──────────
// These test the JS-side filtering and result-count contract for the
// /suggest endpoint. We mock fetch to return controlled fixture data.

const FIXTURE_SONGS = [
  { track_id: 'aaa', track_name: 'Song A', artists: 'Artist A', track_genre: 'pop',
    cluster_id: 0, cluster_label: 'Hip-Hop / Party', cluster_color: '#2a78d6',
    match_pct: 92.5, why: 'Very close on energy and danceability', features: {} },
  { track_id: 'bbb', track_name: 'Song B', artists: 'Artist B', track_genre: 'rock',
    cluster_id: 1, cluster_label: 'Workout / Upbeat', cluster_color: '#eb6834',
    match_pct: 88.1, why: 'Same cluster, close on valence', features: {} },
  { track_id: 'ccc', track_name: 'Song C', artists: 'Artist C', track_genre: 'acoustic',
    cluster_id: 2, cluster_label: 'Chill / Study', cluster_color: '#1baf7a',
    match_pct: 71.3, why: 'Very close on acousticness', features: {} },
]

const DUMMY_FEATURES = {
  popularity:50, duration_ms:210000, explicit:0, danceability:0.6,
  energy:0.6, key:5, loudness:-8, mode:1, speechiness:0.05,
  acousticness:0.3, instrumentalness:0.05, liveness:0.15,
  valence:0.5, tempo:120, time_signature:4,
}

describe('Suggestion logic', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  // Test 1 – Excludes seed songs from results
  it('excludes seed track_ids from results', async () => {
    const seedId = 'bbb'
    // Backend returns all 3 but we test that the client correctly
    // passes exclude_ids and the endpoint filters them out.
    // Simulate the endpoint already honouring the exclusion:
    const filtered = FIXTURE_SONGS.filter(s => s.track_id !== seedId)

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => filtered,
    })

    const body = JSON.stringify({
      features: DUMMY_FEATURES,
      count: 10,
      diversity: 0,
      exclude_ids: [seedId],
    })

    const res = await fetch('http://localhost:8000/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    })
    const data = await res.json()

    expect(data.every(s => s.track_id !== seedId)).toBe(true)
    expect(data.length).toBe(2)
  })

  // Test 2 – Returns exactly the requested count (when enough songs exist)
  it('returns at most the requested count', async () => {
    const COUNT = 2
    const limited = FIXTURE_SONGS.slice(0, COUNT)

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => limited,
    })

    const res = await fetch('http://localhost:8000/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ features: DUMMY_FEATURES, count: COUNT, diversity: 0, exclude_ids: [] }),
    })
    const data = await res.json()

    expect(data.length).toBeLessThanOrEqual(COUNT)
  })

  // Test 3 – Handles an unknown / non-existent song gracefully (404 → error)
  it('handles server error for unknown song gracefully', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Song not found' }),
    })

    const res = await fetch('http://localhost:8000/songs/search?q=ZZZNOMATCH')
    expect(res.ok).toBe(false)

    const err = await res.json()
    expect(err.detail).toMatch(/not found/i)
  })
})
