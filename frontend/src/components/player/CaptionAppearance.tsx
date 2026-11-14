import { Popover, useActiveTextCues, useCaptionsOptions } from '@videojs/react'
import { GearIcon } from '@videojs/react/icons/neutral'
import { usePlayer } from '@videojs/react/video'
import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import type { CaptionFontSize, CaptionPosition, CaptionPreferences } from './captionPreferences'

type Copy = Record<string, string>

interface SharedProps {
  copy: Copy
  preferences: CaptionPreferences
  onChange: (update: Partial<CaptionPreferences>) => void
}

interface OverlayProps {
  preferences: CaptionPreferences
  nativeFullscreen: boolean
}

type SettingsView = 'root' | 'position' | 'fontSize' | 'backgroundOpacity'

const POSITIONS: CaptionPosition[] = ['top', 'center', 'bottom']
const FONT_SIZES: CaptionFontSize[] = ['small', 'medium', 'large']

const positionCopyKey: Record<CaptionPosition, string> = {
  top: 'captionPositionTop',
  center: 'captionPositionCenter',
  bottom: 'captionPositionBottom',
}

const fontSizeCopyKey: Record<CaptionFontSize, string> = {
  small: 'captionSizeSmall',
  medium: 'captionSizeMedium',
  large: 'captionSizeLarge',
}

function moveRadioSelection<T extends string>(event: KeyboardEvent<HTMLInputElement>, values: readonly T[], value: T, setValue: (next: T) => void) {
  const index = values.indexOf(value)
  if (index < 0) return
  if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
    event.preventDefault()
    setValue(values[(index - 1 + values.length) % values.length])
  }
  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
    event.preventDefault()
    setValue(values[(index + 1) % values.length])
  }
}

export function CaptionOverlay({ preferences, nativeFullscreen }: OverlayProps) {
  const captions = useCaptionsOptions()
  const activeCues = useActiveTextCues({ kind: ['captions', 'subtitles'] })

  if (nativeFullscreen || !captions?.state.subtitlesShowing || !activeCues.length) return null

  return <div className={`caption-overlay caption-overlay-${preferences.position} caption-overlay-${preferences.fontSize}`} aria-hidden="true">
    <div className="caption-overlay-stack">
      {activeCues.map(cue => <span className="caption-overlay-cue" key={`${cue.id}-${cue.startTime}`}>
        {cue.text}
      </span>)}
    </div>
  </div>
}

export function CaptionAppearanceMenu({ copy, preferences, onChange }: SharedProps) {
  const captions = useCaptionsOptions()
  const controlsVisible = usePlayer(state => state.controlsVisible)
  const [view, setView] = useState<SettingsView>('root')

  if (captions?.state.availability !== 'available' || !captions.state.subtitlesShowing) return null

  const setPosition = (position: CaptionPosition) => onChange({ position })
  const setFontSize = (fontSize: CaptionFontSize) => onChange({ fontSize })

  return <div className="caption-appearance-control" data-visible={controlsVisible || undefined}>
    <Popover.Root side="left" align="end" boundary="container">
      <Popover.Trigger
        className="caption-appearance-trigger"
        aria-label={copy.captionAppearance}
        onClick={() => setView('root')}
        tabIndex={controlsVisible ? 0 : -1}
        render={<button type="button" />}
      >
        <GearIcon />
      </Popover.Trigger>
      <Popover.Popup className="caption-appearance-popup">
        {view === 'root' && <div className="caption-settings-panel">
          <p className="caption-settings-title">{copy.captionAppearance}</p>
          <button type="button" className="caption-settings-row" onClick={() => setView('position')}>
            <span>{copy.captionPosition}</span><strong>{copy[positionCopyKey[preferences.position]]}</strong>
          </button>
          <button type="button" className="caption-settings-row" onClick={() => setView('fontSize')}>
            <span>{copy.captionSize}</span><strong>{copy[fontSizeCopyKey[preferences.fontSize]]}</strong>
          </button>
          <button type="button" className="caption-settings-row" onClick={() => setView('backgroundOpacity')}>
            <span>{copy.captionBackgroundOpacity}</span><strong>{preferences.backgroundOpacity}%</strong>
          </button>
          <button type="button" className="caption-settings-reset" onClick={() => onChange({ position: 'bottom', fontSize: 'medium', backgroundOpacity: 75 })}>
            {copy.captionReset}
          </button>
        </div>}

        {view === 'position' && <SettingsSection title={copy.captionPosition} backLabel={copy.captionBack} onBack={() => setView('root')}>
          <fieldset className="caption-settings-options">
            <legend className="sr-only">{copy.captionPosition}</legend>
            {POSITIONS.map(position => <label key={position} className="caption-settings-option">
              <input
                type="radio"
                name="caption-position"
                value={position}
                checked={preferences.position === position}
                onChange={() => setPosition(position)}
                onKeyDown={event => moveRadioSelection(event, POSITIONS, position, setPosition)}
              />
              <span>{copy[positionCopyKey[position]]}</span>
            </label>)}
          </fieldset>
        </SettingsSection>}

        {view === 'fontSize' && <SettingsSection title={copy.captionSize} backLabel={copy.captionBack} onBack={() => setView('root')}>
          <fieldset className="caption-settings-options">
            <legend className="sr-only">{copy.captionSize}</legend>
            {FONT_SIZES.map(fontSize => <label key={fontSize} className="caption-settings-option">
              <input
                type="radio"
                name="caption-font-size"
                value={fontSize}
                checked={preferences.fontSize === fontSize}
                onChange={() => setFontSize(fontSize)}
                onKeyDown={event => moveRadioSelection(event, FONT_SIZES, fontSize, setFontSize)}
              />
              <span>{copy[fontSizeCopyKey[fontSize]]}</span>
            </label>)}
          </fieldset>
        </SettingsSection>}

        {view === 'backgroundOpacity' && <SettingsSection title={copy.captionBackgroundOpacity} backLabel={copy.captionBack} onBack={() => setView('root')}>
          <label className="caption-opacity-control" htmlFor="caption-background-opacity">
            <span>{copy.captionBackgroundOpacity}</span>
            <output htmlFor="caption-background-opacity">{preferences.backgroundOpacity}%</output>
          </label>
          <input
            className="caption-opacity-range"
            id="caption-background-opacity"
            type="range"
            min="0"
            max="100"
            step="5"
            value={preferences.backgroundOpacity}
            onChange={event => onChange({ backgroundOpacity: Number(event.target.value) })}
          />
        </SettingsSection>}
      </Popover.Popup>
    </Popover.Root>
  </div>
}

function SettingsSection({ title, backLabel, onBack, children }: { title: string; backLabel: string; onBack: () => void; children: React.ReactNode }) {
  return <div className="caption-settings-panel">
    <div className="caption-settings-heading">
      <button type="button" onClick={onBack} aria-label={backLabel}>‹</button>
      <p className="caption-settings-title">{title}</p>
    </div>
    {children}
  </div>
}
