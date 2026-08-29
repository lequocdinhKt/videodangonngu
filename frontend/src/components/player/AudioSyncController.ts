import { useEffect, useRef, useCallback } from 'react'
import type { LanguageCode } from '../../types'

interface AudioSyncOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>
  audioRef: React.RefObject<HTMLAudioElement | null>
  driftToleranceMs?: number
}

export function useAudioSync({ videoRef, audioRef, driftToleranceMs = 100 }: AudioSyncOptions) {
  const syncing = useRef(false)

  const syncAudio = useCallback(() => {
    const video = videoRef.current
    const audio = audioRef.current
    if (!video || !audio || syncing.current) return

    const drift = Math.abs(audio.currentTime * 1000 - video.currentTime * 1000)
    if (drift > driftToleranceMs) {
      syncing.current = true
      audio.currentTime = video.currentTime
      setTimeout(() => { syncing.current = false }, 50)
    }
  }, [videoRef, audioRef, driftToleranceMs])

  useEffect(() => {
    const video = videoRef.current
    const audio = audioRef.current
    if (!video || !audio) return

    const onPlay = () => { audio.currentTime = video.currentTime; audio.play().catch(() => {}) }
    const onPause = () => audio.pause()
    const onSeeked = () => { audio.currentTime = video.currentTime }
    const onTimeUpdate = () => syncAudio()
    const onEnded = () => audio.pause()

    video.addEventListener('play', onPlay)
    video.addEventListener('pause', onPause)
    video.addEventListener('seeked', onSeeked)
    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('ended', onEnded)

    return () => {
      video.removeEventListener('play', onPlay)
      video.removeEventListener('pause', onPause)
      video.removeEventListener('seeked', onSeeked)
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('ended', onEnded)
    }
  }, [videoRef, audioRef, syncAudio])
}

export function langToShort(code: LanguageCode): string {
  return code.split('-')[0]
}

export function langToAudioUrl(videoId: string, code: LanguageCode): string {
  return `/api/videos/${videoId}/audio/${langToShort(code)}.mp3`
}

export function langToSubtitleUrl(videoId: string, code: LanguageCode): string {
  return `/api/videos/${videoId}/subtitles/${langToShort(code)}.vtt`
}
