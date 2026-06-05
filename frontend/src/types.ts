export interface Episode {
  episode_id: string
  subtitle: string
  situation: string
}

export interface Verse {
  chapter: number
  verse: number
  text: string
}

export interface Passage {
  book: string
  chapter_start: number
  verse_start: number
  chapter_end: number
  verse_end: number
  verses: Verse[]
}

export interface EpisodeDetail {
  episode_id: string
  subtitle: string
  situation: string
  meaning: string
  passages: Passage[]
}

export interface PrayerRecord {
  id: string
  user_id: string
  date: string
  concern: string
  episode_id: string
  subtitle: string
  passage_ref: string
}

export interface Connection {
  type: 'same_episode' | 'similar_concern'
  record: PrayerRecord
  days_ago: number
}
