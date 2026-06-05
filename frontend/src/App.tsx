import { useState, useEffect } from 'react'
import './index.css'
import './App.css'
import type { Episode, EpisodeDetail, Connection } from './types'
import { matchEpisodes, getEpisode, getConnection, savePrayer } from './api'

type Step = 'name' | 'concern' | 'episodes' | 'detail'

const STORAGE_KEY = 'areum_user'

function passageRef(ep: EpisodeDetail): string {
  const p = ep.passages[0]
  return `${p.book} ${p.chapter_start}:${p.verse_start}-${p.chapter_end}:${p.verse_end}`
}

export default function App() {
  const [step, setStep] = useState<Step>('name')
  const [userName, setUserName] = useState('')
  const [nameInput, setNameInput] = useState('')
  const [concern, setConcern] = useState('')
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [detail, setDetail] = useState<EpisodeDetail | null>(null)
  const [connection, setConnection] = useState<Connection | null>(null)
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      setUserName(stored)
      setStep('concern')
    }
  }, [])

  // ── 이름 입력 ──────────────────────────────────────────────
  if (step === 'name') {
    const handleName = () => {
      const name = nameInput.trim()
      if (!name) return
      localStorage.setItem(STORAGE_KEY, name)
      setUserName(name)
      setStep('concern')
    }
    return (
      <div className="screen">
        <div className="screen-title">
          <h1>아름</h1>
          <p>말씀으로 기도를 시작합니다.</p>
        </div>
        <div className="gap">
          <div>
            <div className="label">이름</div>
            <input
              type="text"
              placeholder="이름을 입력해 주세요"
              value={nameInput}
              onChange={e => setNameInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleName()}
              autoFocus
            />
          </div>
          <button className="btn-primary" onClick={handleName} disabled={!nameInput.trim()}>
            시작하기
          </button>
        </div>
      </div>
    )
  }

  // ── 고민 입력 ──────────────────────────────────────────────
  if (step === 'concern') {
    const handleMatch = async () => {
      if (!concern.trim()) return
      setLoading(true)
      setSaved(false)
      try {
        const eps = await matchEpisodes(concern.trim())
        setEpisodes(eps)
        setStep('episodes')
      } finally {
        setLoading(false)
      }
    }
    return (
      <div className="screen">
        <div className="screen-title">
          <h1>안녕하세요, {userName}님</h1>
          <p>오늘 어떤 고민이나 기도제목이 있으신가요?</p>
        </div>
        {saved && <div className="success-msg">기도가 기록되었습니다.</div>}
        <div className="gap">
          <textarea
            rows={5}
            placeholder="마음에 담긴 것을 자유롭게 적어 주세요."
            value={concern}
            onChange={e => setConcern(e.target.value)}
            autoFocus
          />
          <button
            className="btn-primary"
            onClick={handleMatch}
            disabled={!concern.trim() || loading}
          >
            {loading ? '말씀을 찾는 중…' : '관련 말씀 찾기'}
          </button>
        </div>
        <button
          className="back-btn"
          onClick={() => {
            localStorage.removeItem(STORAGE_KEY)
            setUserName('')
            setStep('name')
          }}
        >
          이름 변경
        </button>
      </div>
    )
  }

  // ── 에피소드 카드 선택 ────────────────────────────────────
  if (step === 'episodes') {
    const labels = ['A', 'B', 'C']
    const handleSelect = async (ep: Episode) => {
      setLoading(true)
      try {
        const [det, conn] = await Promise.all([
          getEpisode(ep.episode_id),
          getConnection(userName, concern, ep.episode_id),
        ])
        setDetail(det)
        setConnection(conn)
        setStep('detail')
      } finally {
        setLoading(false)
      }
    }
    return (
      <div className="screen">
        <div className="screen-title">
          <h1>관련 말씀</h1>
          <p>어떤 말씀이 마음에 와닿으시나요?</p>
        </div>
        {loading ? (
          <div className="spinner">불러오는 중…</div>
        ) : (
          <div className="gap-lg">
            {episodes.map((ep, i) => (
              <button key={ep.episode_id} className="card-btn" onClick={() => handleSelect(ep)}>
                <div className="episode-label">{labels[i]}</div>
                <div style={{ fontWeight: 600, fontSize: 16 }}>{ep.subtitle}</div>
                {ep.situation && (
                  <div className="episode-situation">{ep.situation}</div>
                )}
              </button>
            ))}
          </div>
        )}
        <button className="back-btn" onClick={() => setStep('concern')}>← 고민 다시 입력</button>
      </div>
    )
  }

  // ── 에피소드 상세 + 기도 확인 ─────────────────────────────
  if (step === 'detail' && detail) {
    const ref = passageRef(detail)
    const mainPassage = detail.passages[0]

    const handlePray = async () => {
      setLoading(true)
      try {
        await savePrayer(userName, concern, detail.episode_id, detail.subtitle, ref)
        setSaved(true)
        setConcern('')
        setStep('concern')
      } finally {
        setLoading(false)
      }
    }

    return (
      <div className="screen">
        <button className="back-btn" onClick={() => setStep('episodes')}>← 다른 말씀 보기</button>

        {/* 에피소드 제목 + 구절 */}
        <div className="card gap-lg">
          <div>
            <h2>{detail.subtitle}</h2>
            <div className="passage-ref">{ref}</div>
            <div className="verse-block">
              {mainPassage.verses.map(v => (
                <span key={`${v.chapter}-${v.verse}`}>
                  <sup className="verse-num">{v.verse}</sup>
                  {v.text}{' '}
                </span>
              ))}
            </div>
          </div>

          {detail.meaning && (
            <div>
              <div className="label">의미</div>
              <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>{detail.meaning}</p>
            </div>
          )}
        </div>

        {/* 기도 연결고리 */}
        {connection && (
          <div className="connection-box">
            {connection.days_ago === 0 ? '오늘' : `${connection.days_ago}일 전`}
            {' '}— "{connection.record.concern}"
            <br />
            {connection.type === 'same_episode'
              ? '→ 그때도 이 말씀을 받으셨어요.'
              : `→ 그때는 ${connection.record.subtitle}을(를) 받으셨어요.`}
          </div>
        )}

        {/* 기도 여부 */}
        <div className="prayer-prompt">
          <p>이 말씀으로 기도하셨나요?</p>
          <div className="btn-row">
            <button className="btn-primary" onClick={handlePray} disabled={loading}>
              네
            </button>
            <button
              className="btn-outline"
              onClick={() => { setConcern(''); setStep('concern') }}
            >
              아니요
            </button>
          </div>
        </div>
      </div>
    )
  }

  return null
}
