import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LANGUAGES, type LanguageCode } from '../../types'

export default function LanguageSelectPage() {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<LanguageCode>('en-US')

  const handleContinue = () => {
    localStorage.setItem('preferredLanguage', selected)
    navigate('/videos')
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <h1 className="text-3xl font-bold mb-2">Select Language</h1>
      <p className="text-gray-400 mb-8">Choose your preferred language</p>

      <div className="w-full max-w-sm space-y-3">
        {LANGUAGES.map(lang => (
          <button
            key={lang.code}
            onClick={() => setSelected(lang.code)}
            className={`w-full flex items-center gap-4 p-4 rounded-xl border transition ${
              selected === lang.code
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-gray-700 bg-gray-900 hover:border-gray-500'
            }`}
          >
            <span className="text-2xl">{lang.flag}</span>
            <span className="text-lg">{lang.label}</span>
          </button>
        ))}
      </div>

      <button
        onClick={handleContinue}
        className="mt-8 w-full max-w-sm py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-semibold transition"
      >
        Continue
      </button>
    </div>
  )
}
