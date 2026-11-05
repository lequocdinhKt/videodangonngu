import { useEffect, useMemo, useRef, useState } from 'react'
import type { LanguageCode, Video } from '../../types'
import { LANGUAGES, UI_COPY } from '../../types'

interface Props {
  video: Video
  initialLanguage: LanguageCode
}

export default function VideoPlayer({ video, initialLanguage }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [subtitleLanguage, setSubtitleLanguage] = useState<LanguageCode>(initialLanguage)
  const [subtitlesEnabled, setSubtitlesEnabled] = useState(true)
  const [trackUrl, setTrackUrl] = useState<string | null>(null)
  const copy = UI_COPY[initialLanguage]
  const available = useMemo(
    () => LANGUAGES.filter(language => video.languages.some(track => track.language_code === language.code && track.subtitle_url)),
    [video.languages],
  )

  useEffect(() => {
    if (!available.some(item => item.code === subtitleLanguage)) {
      setSubtitleLanguage((available[0]?.code || 'vi-VN') as LanguageCode)
    }
  }, [available, subtitleLanguage])

  useEffect(() => {
    const source = video.languages.find(item => item.language_code === subtitleLanguage)?.subtitle_url
    if (!source || !subtitlesEnabled) {
      setTrackUrl(null)
      return
    }
    let currentUrl: string | null = null
    let cancelled = false
    fetch(source)
      .then(response => {
        if (!response.ok) throw new Error('Subtitle unavailable')
        return response.blob()
      })
      .then(blob => {
        if (cancelled) return
        currentUrl = URL.createObjectURL(blob)
        setTrackUrl(currentUrl)
      })
      .catch(() => setTrackUrl(null))
    return () => {
      cancelled = true
      if (currentUrl) URL.revokeObjectURL(currentUrl)
    }
  }, [subtitleLanguage, subtitlesEnabled, video.languages])

  const toggleFullscreen = async () => {
    if (!containerRef.current) return
    if (document.fullscreenElement) await document.exitFullscreen()
    else await containerRef.current.requestFullscreen()
  }

  return (
    <div ref={containerRef} className="video-shell" onContextMenu={event => event.preventDefault()}>
      <video
        key={`${video.video_url}-${trackUrl}`}
        src={video.video_url || undefined}
        poster={video.thumbnail_url || undefined}
        controls
        controlsList="nodownload noremoteplayback"
        disablePictureInPicture
        playsInline
        className="video-element"
      >
        {trackUrl && (
          <track
            key={trackUrl}
            src={trackUrl}
            kind="subtitles"
            srcLang={subtitleLanguage.split('-')[0]}
            label={LANGUAGES.find(item => item.code === subtitleLanguage)?.nativeLabel}
            default
          />
        )}
      </video>

      <div className="player-toolbar">
        <label className="control-group">
          <span>{copy.subtitles}</span>
          <select
            value={subtitlesEnabled ? subtitleLanguage : 'off'}
            onChange={event => {
              if (event.target.value === 'off') setSubtitlesEnabled(false)
              else {
                setSubtitlesEnabled(true)
                setSubtitleLanguage(event.target.value as LanguageCode)
              }
            }}
          >
            <option value="off">{copy.subtitlesOff}</option>
            {available.map(item => <option key={item.code} value={item.code}>{item.flag} {item.nativeLabel}</option>)}
          </select>
        </label>
        <button type="button" className="icon-button" onClick={toggleFullscreen} aria-label={copy.fullscreen}>
          <span aria-hidden>⛶</span> {copy.fullscreen}
        </button>
      </div>
    </div>
  )
}
