import '@videojs/react/video/neutral-skin.css'
import { NeutralVideoSkin, Video, VideoPlayer as VideoJsPlayer } from '@videojs/react/video'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import type { LanguageCode, Video as VideoModel } from '../../types'
import { LANGUAGES, UI_COPY } from '../../types'
import { CaptionAppearanceMenu, CaptionOverlay } from './CaptionAppearance'
import { readCaptionPreferences, saveCaptionPreferences } from './captionPreferences'
import type { CaptionPreferences } from './captionPreferences'

interface Props { video: VideoModel; initialLanguage: LanguageCode }

/**
 * Video.js owns playback, responsive controls, nested settings menus and the
 * selected TextTrack. Keeping this surface in a maintained media component
 * avoids the browser-state races that occurred with our hand-built controls.
 */
export default function VideoPlayer({ video, initialLanguage }: Props) {
  const playerRef = useRef<HTMLDivElement>(null)
  const copy = UI_COPY[initialLanguage]
  const hasVideo = Boolean(video.video_url)
  const tracks = LANGUAGES.flatMap(language => {
    const source = video.languages.find(item => item.language_code === language.code)?.subtitle_url
    return source ? [{ ...language, source }] : []
  })

  if (!hasVideo) {
    return <div className="video-shell is-preview" role="status">
      <div className="video-stage"><img className="video-element" src={video.thumbnail_url || undefined} alt="" /></div>
      <div className="player-preview-label"><span />{copy.videoComingSoon}</div>
    </div>
  }

  return <Player video={video} initialLanguage={initialLanguage} tracks={tracks} playerRef={playerRef} />
}

type PlayerProps = Pick<Props, 'video' | 'initialLanguage'> & {
  tracks: Array<(typeof LANGUAGES)[number] & { source: string }>
  playerRef: React.RefObject<HTMLDivElement | null>
}

type LockableScreenOrientation = ScreenOrientation & {
  lock?: (orientation: 'landscape') => Promise<void>
}

function Player({ video, initialLanguage, tracks, playerRef }: PlayerProps) {
  const [captionPreferences, setCaptionPreferences] = useState<CaptionPreferences>(readCaptionPreferences)
  const [nativeFullscreen, setNativeFullscreen] = useState(false)
  const copy = UI_COPY[initialLanguage]

  const updateCaptionPreferences = useCallback((update: Partial<CaptionPreferences>) => {
    setCaptionPreferences(current => {
      const next = { ...current, ...update }
      saveCaptionPreferences(next)
      return next
    })
  }, [])

  useEffect(() => {
    const orientation = screen.orientation as LockableScreenOrientation
    const syncOrientation = () => {
      if (document.fullscreenElement) {
        // Browsers allow orientation locking only after the user requests fullscreen.
        void orientation?.lock?.('landscape').catch(() => undefined)
        return
      }
      orientation?.unlock?.()
    }

    const videoElement = playerRef.current?.querySelector('video')
    const lockLandscape = () => {
      setNativeFullscreen(true)
      void orientation?.lock?.('landscape').catch(() => undefined)
    }
    const unlockOrientation = () => {
      setNativeFullscreen(false)
      orientation?.unlock?.()
    }

    document.addEventListener('fullscreenchange', syncOrientation)
    videoElement?.addEventListener('webkitbeginfullscreen', lockLandscape)
    videoElement?.addEventListener('webkitendfullscreen', unlockOrientation)

    return () => {
      document.removeEventListener('fullscreenchange', syncOrientation)
      videoElement?.removeEventListener('webkitbeginfullscreen', lockLandscape)
      videoElement?.removeEventListener('webkitendfullscreen', unlockOrientation)
      orientation?.unlock?.()
    }
  }, [playerRef])

  const skinClassName = `videojs-skin caption-overlay-enabled${nativeFullscreen ? ' is-native-video-fullscreen' : ''}`
  const skinStyle = {
    width: '100%',
    height: '100%',
    '--media-caption-track-y': 'calc(var(--media-spacing) * -17)',
    '--caption-background-opacity': String(captionPreferences.backgroundOpacity / 100),
  } as CSSProperties

  return <div ref={playerRef} className="video-shell videojs-shell" onContextMenu={event => event.preventDefault()}>
    <div className="videojs-aspect-frame">
      <VideoJsPlayer key={video.video_url || video.id} title={video.title} poster={video.thumbnail_url || undefined}>
        <NeutralVideoSkin className={skinClassName} style={skinStyle}>
        <Video src={video.video_url || undefined} poster={video.thumbnail_url || undefined} preload="metadata" playsInline crossOrigin="anonymous" controlsList="nodownload noremoteplayback" disablePictureInPicture>
          {tracks.map(track => <track key={track.code} kind="subtitles" src={track.source} srcLang={track.short} label={track.nativeLabel} default={track.code === initialLanguage} />)}
        </Video>
        <CaptionOverlay preferences={captionPreferences} nativeFullscreen={nativeFullscreen} />
        <CaptionAppearanceMenu copy={copy} preferences={captionPreferences} onChange={updateCaptionPreferences} />
        </NeutralVideoSkin>
      </VideoJsPlayer>
    </div>
  </div>
}
