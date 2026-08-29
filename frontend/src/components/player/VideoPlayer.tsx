import { useEffect, useRef, useState, useCallback } from 'react'
import type { LanguageCode, SubtitleSettings, Video } from '../../types'
import { LANGUAGES, DEFAULT_SUBTITLE_SETTINGS } from '../../types'
import { useAudioSync, langToAudioUrl, langToSubtitleUrl } from './AudioSyncController'

interface Props {
  video: Video
  initialLanguage: LanguageCode
}

function parseVTT(vtt: string): { start: number; end: number; text: string }[] {
  const cues: { start: number; end: number; text: string }[] = []
  const blocks = vtt.replace(/^WEBVTT\s*\n/, '').trim().split(/\n\n+/)
  for (const block of blocks) {
    const lines = block.split('\n')
    const timeLine = lines.find(l => l.includes('-->'))
    if (!timeLine) continue
    const [startStr, endStr] = timeLine.split('-->').map(s => s.trim())
    const text = lines.slice(lines.indexOf(timeLine) + 1).join('\n')
    cues.push({ start: vttTimeToSec(startStr), end: vttTimeToSec(endStr), text })
  }
  return cues
}

function vttTimeToSec(t: string): number {
  const [h, m, rest] = t.split(':')
  const [s, ms] = rest.split('.')
  return +h * 3600 + +m * 60 + +s + +ms / 1000
}

export default function VideoPlayer({ video, initialLanguage }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const [selectedLang, setSelectedLang] = useState<LanguageCode>(initialLanguage)
  const [audioLang, setAudioLang] = useState<LanguageCode>(initialLanguage)
  const [dubbing, setDubbing] = useState(true)
  const [subtitleLang, setSubtitleLang] = useState<LanguageCode>(initialLanguage)
  const [cues, setCues] = useState<{ start: number; end: number; text: string }[]>([])
  const [currentCue, setCurrentCue] = useState('')
  const [settings, setSettings] = useState<SubtitleSettings>(DEFAULT_SUBTITLE_SETTINGS)
  const [showControls, setShowControls] = useState(false)

  useAudioSync({ videoRef, audioRef })

  const effectiveAudioLang = dubbing ? audioLang : 'vi-VN'

  const switchAudio = useCallback((lang: LanguageCode) => {
    const audio = audioRef.current
    const videoEl = videoRef.current
    if (!audio || !videoEl) return
    const wasPlaying = !videoEl.paused
    const time = videoEl.currentTime
    audio.src = langToAudioUrl(video.id, lang)
    audio.load()
    audio.currentTime = time
    if (wasPlaying) audio.play().catch(() => {})
  }, [video.id])

  useEffect(() => { switchAudio(effectiveAudioLang) }, [effectiveAudioLang, switchAudio])

  useEffect(() => {
    fetch(langToSubtitleUrl(video.id, subtitleLang))
      .then(r => r.text())
      .then(text => setCues(parseVTT(text)))
      .catch(() => setCues([]))
  }, [video.id, subtitleLang])

  useEffect(() => {
    const videoEl = videoRef.current
    if (!videoEl) return
    const onTime = () => {
      const t = videoEl.currentTime
      const cue = cues.find(c => t >= c.start && t <= c.end)
      setCurrentCue(cue?.text || '')
    }
    videoEl.addEventListener('timeupdate', onTime)
    return () => videoEl.removeEventListener('timeupdate', onTime)
  }, [cues])

  const toggleFullscreen = () => {
    const el = containerRef.current
    if (!el) return
    if (document.fullscreenElement) document.exitFullscreen()
    else el.requestFullscreen()
  }

  const positionClass = settings.position === 'top' ? 'top-4' : settings.position === 'center' ? 'top-1/2 -translate-y-1/2' : 'bottom-16'

  return (
    <div ref={containerRef} className="relative w-full bg-black rounded-lg overflow-hidden">
      <video
        ref={videoRef}
        src={video.video_url || ''}
        className="w-full aspect-video"
        playsInline
        onClick={() => {
          const v = videoRef.current
          if (v) v.paused ? v.play() : v.pause()
        }}
      />
      <audio ref={audioRef} />

      {settings.enabled && currentCue && (
        <div className={`absolute left-0 right-0 ${positionClass} flex justify-center px-4 pointer-events-none z-10`}>
          <span
            style={{
              fontSize: settings.fontSize,
              color: settings.textColor,
              backgroundColor: settings.bgColor,
              padding: '4px 12px',
              borderRadius: '4px',
              maxWidth: '90%',
              textAlign: 'center',
            }}
            className="subtitle-text"
          >
            <span style={{ opacity: settings.textOpacity }}>{currentCue}</span>
          </span>
        </div>
      )}

      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 p-3 space-y-2">
        <div className="flex gap-2 flex-wrap">
          <select
            value={selectedLang}
            onChange={e => {
              const lang = e.target.value as LanguageCode
              setSelectedLang(lang)
              setSubtitleLang(lang)
              if (dubbing) setAudioLang(lang)
            }}
            className="bg-gray-800 text-sm px-2 py-1 rounded"
          >
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.flag} {l.label}</option>)}
          </select>

          <select
            value={audioLang}
            onChange={e => setAudioLang(e.target.value as LanguageCode)}
            className="bg-gray-800 text-sm px-2 py-1 rounded"
          >
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>Audio: {l.label}</option>)}
          </select>

          <select
            value={subtitleLang}
            onChange={e => setSubtitleLang(e.target.value as LanguageCode)}
            className="bg-gray-800 text-sm px-2 py-1 rounded"
          >
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>Sub: {l.label}</option>)}
          </select>

          <label className="flex items-center gap-1 text-sm">
            <input type="checkbox" checked={dubbing} onChange={e => setDubbing(e.target.checked)} />
            Dubbing
          </label>

          <button onClick={toggleFullscreen} className="bg-gray-700 px-2 py-1 rounded text-sm ml-auto">
            Fullscreen
          </button>
          <button onClick={() => setShowControls(!showControls)} className="bg-gray-700 px-2 py-1 rounded text-sm">
            Subtitle Style
          </button>
        </div>

        {showControls && (
          <div className="grid grid-cols-2 gap-2 text-sm bg-gray-900/90 p-2 rounded">
            <label>Size <input type="range" min={12} max={32} value={settings.fontSize} onChange={e => setSettings(s => ({ ...s, fontSize: +e.target.value }))} /></label>
            <label>Text Color <input type="color" value={settings.textColor} onChange={e => setSettings(s => ({ ...s, textColor: e.target.value }))} /></label>
            <label>Text Opacity <input type="range" min={0} max={1} step={0.1} value={settings.textOpacity} onChange={e => setSettings(s => ({ ...s, textOpacity: +e.target.value }))} /></label>
            <label>BG Color <input type="color" value={settings.bgColor} onChange={e => setSettings(s => ({ ...s, bgColor: e.target.value }))} /></label>
            <label>BG Opacity <input type="range" min={0} max={1} step={0.1} value={settings.bgOpacity} onChange={e => setSettings(s => ({ ...s, bgOpacity: +e.target.value }))} /></label>
            <label>Position
              <select value={settings.position} onChange={e => setSettings(s => ({ ...s, position: e.target.value as SubtitleSettings['position'] }))} className="bg-gray-800 ml-1">
                <option value="top">Top</option>
                <option value="center">Center</option>
                <option value="bottom">Bottom</option>
              </select>
            </label>
            <label className="col-span-2"><input type="checkbox" checked={settings.enabled} onChange={e => setSettings(s => ({ ...s, enabled: e.target.checked }))} /> Show Subtitles</label>
          </div>
        )}
      </div>
    </div>
  )
}
