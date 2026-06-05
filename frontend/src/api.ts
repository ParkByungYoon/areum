import type { Episode, EpisodeDetail, Connection, PrayerRecord } from './types'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${path} ${res.status}`)
  return res.json()
}

export async function matchEpisodes(concern: string): Promise<Episode[]> {
  return post('/api/match', { concern })
}

export async function getEpisode(episodeId: string): Promise<EpisodeDetail> {
  const res = await fetch(`/api/episode/${encodeURIComponent(episodeId)}`)
  if (!res.ok) throw new Error(`episode ${res.status}`)
  return res.json()
}

export async function getConnection(
  userId: string,
  concern: string,
  episodeId: string,
): Promise<Connection | null> {
  return post('/api/connection', { user_id: userId, concern, episode_id: episodeId })
}

export async function savePrayer(
  userId: string,
  concern: string,
  episodeId: string,
  subtitle: string,
  passageRef: string,
): Promise<PrayerRecord> {
  return post('/api/prayer', {
    user_id: userId,
    concern,
    episode_id: episodeId,
    subtitle,
    passage_ref: passageRef,
  })
}
