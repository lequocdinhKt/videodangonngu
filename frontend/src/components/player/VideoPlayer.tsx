import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties, KeyboardEvent } from 'react'
import type { LanguageCode, Video } from '../../types'
import { LANGUAGES, UI_COPY } from '../../types'

interface Props { video: Video; initialLanguage: LanguageCode }

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
  return `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`
}

function PlayIcon({ paused }: { paused: boolean }) {
  return paused ? <svg viewBox="0 0 24 24" aria-hidden><path d="M8 5v14l11-7z" /></svg> : <svg viewBox="0 0 24 24" aria-hidden><path d="M6 5h4v14H6zm8 0h4v14h-4z" /></svg>
}

function VolumeIcon({ muted }: { muted: boolean }) {
  return <svg viewBox="0 0 24 24" aria-hidden><path d="M4 9v6h4l5 4V5L8 9H4z" />{muted ? <path d="m17 9 4 4m0-4-4 4" fill="none" stroke="currentColor" strokeWidth="2" /> : <path d="M16 8.5a5 5 0 1 1 0 7" fill="none" stroke="currentColor" strokeWidth="2" />}</svg>
}

function SettingsIcon() { return <svg viewBox="0 0 24 24" aria-hidden><path d="M12 8.2a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6Zm8 3.8 2-1.5-2-3.5-2.35.95a7.9 7.9 0 0 0-1.62-.94L15.7 4.5h-4l-.33 2.54c-.57.23-1.12.54-1.62.94L7.4 7.03l-2 3.47L7.4 12c-.03.3-.03.6 0 .9l-2 1.52 2 3.46 2.35-.94c.5.4 1.05.7 1.62.93l.33 2.54h4l.33-2.54c.57-.23 1.12-.54 1.62-.93l2.35.94 2-3.46-2-1.52c.03-.3.03-.6 0-.9Z" /></svg> }
function FullscreenIcon() { return <svg viewBox="0 0 24 24" aria-hidden><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" fill="none" stroke="currentColor" strokeWidth="2" /></svg> }

export default function VideoPlayer({ video, initialLanguage }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const settingsButtonRef = useRef<HTMLButtonElement>(null)
  const hideControlsTimer = useRef<number | undefined>(undefined)
  const [subtitleLanguage, setSubtitleLanguage] = useState<LanguageCode>(initialLanguage)
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [trackUrl, setTrackUrl] = useState<string | null>(null)
  const [playing, setPlaying] = useState(false)
  const [controlsVisible, setControlsVisible] = useState(true)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState((video.duration_ms || 0) / 1000)
  const [muted, setMuted] = useState(false)
  const [playbackRate, setPlaybackRate] = useState(1)
  const copy = UI_COPY[initialLanguage]
  const hasVideo = Boolean(video.video_url)
  const available = useMemo(() => LANGUAGES.filter(language => video.languages.some(track => track.language_code === language.code && track.subtitle_url)), [video.languages])

  const revealControls = () => {
    window.clearTimeout(hideControlsTimer.current)
    setControlsVisible(true)
    if (playing && !settingsOpen) hideControlsTimer.current = window.setTimeout(() => setControlsVisible(false), 2600)
  }

  useEffect(() => () => window.clearTimeout(hideControlsTimer.current), [])
  useEffect(() => { if (available.length > 0 && !available.some(item => item.code === subtitleLanguage)) setSubtitleLanguage((available[0]?.code || 'vi-VN') as LanguageCode) }, [available, subtitleLanguage])
  useEffect(() => {
    const source = video.languages.find(item => item.language_code === subtitleLanguage)?.subtitle_url
    if (!source || !subtitlesEnabled) { setTrackUrl(null); return }
    let currentUrl: string | null = null
    let cancelled = false
    fetch(source).then(response => { if (!response.ok) throw new Error('Subtitle unavailable'); return response.blob() }).then(blob => {
      if (cancelled) return
      currentUrl = URL.createObjectURL(blob)
      setTrackUrl(currentUrl)
    }).catch(() => setTrackUrl(null))
    return () => { cancelled = true; if (currentUrl) URL.revokeObjectURL(currentUrl) }
  }, [subtitleLanguage, subtitlesEnabled, video.languages])
  useEffect(() => { setPlaying(false); setCurrentTime(0); setDuration((video.duration_ms || 0) / 1000); setControlsVisible(true); setSettingsOpen(false) }, [video.duration_ms, video.video_url])
  useEffect(() => { if (videoRef.current) videoRef.current.playbackRate = playbackRate }, [playbackRate])

  const togglePlayback = async () => {
    const element = videoRef.current
    if (!element || !hasVideo) return
    if (element.paused) await element.play(); else element.pause()
    revealControls()
  }
  const toggleMute = () => { const element = videoRef.current; if (!element) return; element.muted = !element.muted; setMuted(element.muted); revealControls() }
  const seekBy = (seconds: number) => {
    const element = videoRef.current
    if (!element || !hasVideo) return
    const next = Math.min(Math.max(0, element.currentTime + seconds), duration || element.duration || 0)
    element.currentTime = next; setCurrentTime(next); revealControls()
  }
  const toggleFullscreen = async () => { if (!containerRef.current) return; if (document.fullscreenElement) await document.exitFullscreen(); else await containerRef.current.requestFullscreen(); revealControls() }
  const closeSettings = () => { setSettingsOpen(false); settingsButtonRef.current?.focus() }
  const handleKeyboard = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape' && settingsOpen) { event.preventDefault(); closeSettings(); return }
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLButtonElement) return
    const key = event.key.toLowerCase()
    if (event.key === ' ' || key === 'k') { event.preventDefault(); void togglePlayback() }
    else if (key === 'm') toggleMute()
    else if (key === 'f') void toggleFullscreen()
    else if (key === 'j' || event.key === 'ArrowLeft') { event.preventDefault(); seekBy(-5) }
    else if (key === 'l' || event.key === 'ArrowRight') { event.preventDefault(); seekBy(5) }
  }
  const settingsLabel = initialLanguage === 'vi-VN' ? 'Cài đặt video' : initialLanguage === 'ru-RU' ? 'Настройки видео' : initialLanguage === 'zh-CN' ? '视频设置' : 'Video settings'
  const speedLabel = initialLanguage === 'vi-VN' ? 'Tốc độ phát' : initialLanguage === 'ru-RU' ? 'Скорость' : initialLanguage === 'zh-CN' ? '播放速度' : 'Playback speed'

  return <div ref={containerRef} className={`video-shell custom-video-player ${hasVideo ? '' : 'is-preview'} ${controlsVisible || !playing || settingsOpen ? 'controls-visible' : 'controls-hidden'}`} onContextMenu={event => event.preventDefault()} onKeyDown={handleKeyboard} onPointerMove={revealControls} onFocusCapture={revealControls} tabIndex={0}>
    <div className="video-stage" onClick={() => void togglePlayback()}>
      <video ref={videoRef} src={video.video_url || undefined} poster={video.thumbnail_url || undefined} preload="metadata" controlsList="nodownload noremoteplayback" disablePictureInPicture playsInline className="video-element" onPlay={() => { setPlaying(true); revealControls() }} onPause={() => { setPlaying(false); setControlsVisible(true) }} onTimeUpdate={event => setCurrentTime(event.currentTarget.currentTime)} onLoadedMetadata={event => setDuration(event.currentTarget.duration || 0)} onEnded={() => { setPlaying(false); setControlsVisible(true) }}>
        {trackUrl && <track key={trackUrl} src={trackUrl} kind="subtitles" srcLang={subtitleLanguage.split('-')[0]} label={LANGUAGES.find(item => item.code === subtitleLanguage)?.nativeLabel} default />}
      </video>
      {!playing && <button type="button" className="player-center-button" onClick={event => { event.stopPropagation(); void togglePlayback() }} disabled={!hasVideo} aria-label={copy.play}><PlayIcon paused /></button>}
      {!hasVideo && <div className="player-preview-label"><span />{copy.videoComingSoon}</div>}
    </div>
    <div className="player-controls" onClick={event => event.stopPropagation()}>
      <input className="player-progress" type="range" min="0" max={duration || 0} step="0.1" value={Math.min(currentTime, duration || 0)} disabled={!hasVideo} style={{ '--progress': `${duration ? (currentTime / duration) * 100 : 0}%` } as CSSProperties} onChange={event => { const next = Number(event.target.value); if (videoRef.current) videoRef.current.currentTime = next; setCurrentTime(next) }} aria-label={copy.seek} />
      <div className="player-control-row">
        <div className="player-control-cluster">
          <button type="button" className="player-control-button" onClick={() => void togglePlayback()} disabled={!hasVideo} aria-label={playing ? copy.pause : copy.play}><PlayIcon paused={!playing} /></button>
          <button type="button" className="player-control-button" onClick={toggleMute} disabled={!hasVideo} aria-label={muted ? copy.unmute : copy.mute}><VolumeIcon muted={muted} /></button>
          <span className="player-time">{formatTime(currentTime)} <i>/</i> {formatTime(duration)}</span>
        </div>
        <div className="player-control-cluster player-control-actions">
          <button type="button" className={`player-control-button cc-button ${subtitlesEnabled ? 'is-active' : ''}`} onClick={() => { setSubtitlesEnabled(enabled => !enabled); revealControls() }} disabled={available.length === 0} aria-label={copy.subtitles} aria-pressed={subtitlesEnabled}>CC</button>
          <div className="settings-control-wrap">
            {settingsOpen && <div className="player-settings-menu" role="menu" aria-label={settingsLabel}>
              <section><p>{copy.subtitles}</p><div role="group" aria-label={copy.subtitles}>
                <button type="button" role="menuitemradio" aria-checked={!subtitlesEnabled} className={!subtitlesEnabled ? 'is-selected' : ''} onClick={() => { setSubtitlesEnabled(false); closeSettings() }}><span>{copy.subtitlesOff}</span>{!subtitlesEnabled && <b aria-hidden>✓</b>}</button>
                {LANGUAGES.map(item => { const isAvailable = available.some(track => track.code === item.code); const isSelected = subtitlesEnabled && subtitleLanguage === item.code; return <button type="button" key={item.code} role="menuitemradio" aria-checked={isSelected} className={`${isSelected ? 'is-selected' : ''} ${!isAvailable ? 'is-unavailable' : ''}`} disabled={!isAvailable} onClick={() => { setSubtitlesEnabled(true); setSubtitleLanguage(item.code); closeSettings() }}><span><strong>{item.nativeLabel}</strong>{!isAvailable && <small>{copy.subtitleUnavailable}</small>}</span>{isSelected && <b aria-hidden>✓</b>}</button> })}
              </div></section>
              <section><p>{speedLabel}</p><div className="playback-rates" role="group" aria-label={speedLabel}>
                {[0.75, 1, 1.25, 1.5].map(rate => <button type="button" key={rate} role="menuitemradio" aria-checked={playbackRate === rate} className={playbackRate === rate ? 'is-selected' : ''} onClick={() => { setPlaybackRate(rate); closeSettings() }}><span>{rate === 1 ? '1×' : `${rate}×`}</span>{playbackRate === rate && <b aria-hidden>✓</b>}</button>)}
              </div></section>
            </div>}
            <button ref={settingsButtonRef} type="button" className="player-control-button" onClick={() => { setSettingsOpen(open => !open); revealControls() }} aria-label={settingsLabel} aria-expanded={settingsOpen}><SettingsIcon /></button>
          </div>
          <button type="button" className="player-control-button" onClick={() => void toggleFullscreen()} aria-label={copy.fullscreen}><FullscreenIcon /></button>
        </div>
      </div>
    </div>
  </div>
}
