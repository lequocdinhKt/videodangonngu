import '@videojs/react/video/neutral-skin.css'
import { NeutralVideoSkin, Video, VideoPlayer as VideoJsPlayer } from '@videojs/react/video'
import type { CSSProperties } from 'react'
import type { LanguageCode, Video as VideoModel } from '../../types'
import { LANGUAGES, UI_COPY } from '../../types'

interface Props { video: VideoModel; initialLanguage: LanguageCode }

/**
 * Video.js owns playback, responsive controls, nested settings menus and the
 * selected TextTrack. Keeping this surface in a maintained media component
 * avoids the browser-state races that occurred with our hand-built controls.
 */
export default function VideoPlayer({ video, initialLanguage }: Props) {
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

  return <div className="video-shell videojs-shell" onContextMenu={event => event.preventDefault()}>
    <div className="videojs-aspect-frame">
      <VideoJsPlayer key={video.video_url || video.id} title={video.title} poster={video.thumbnail_url || undefined}>
        <NeutralVideoSkin className="videojs-skin" style={{ width: '100%', height: '100%', '--media-caption-track-y': 'calc(var(--media-spacing) * -17)' } as CSSProperties}>
        <Video src={video.video_url || undefined} poster={video.thumbnail_url || undefined} preload="metadata" playsInline crossOrigin="anonymous" controlsList="nodownload noremoteplayback" disablePictureInPicture>
          {tracks.map(track => <track key={track.code} kind="subtitles" src={track.source} srcLang={track.short} label={track.nativeLabel} default={track.code === initialLanguage} />)}
        </Video>
        </NeutralVideoSkin>
      </VideoJsPlayer>
    </div>
  </div>
}
