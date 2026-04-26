import { createContext, useContext, useState, useEffect, useRef } from 'react'

const ThemeContext = createContext()

export function ThemeProvider({ children }) {
  // Track whether user has manually toggled (vs. auto-detected from OS)
  const manuallySet = useRef(localStorage.getItem('vietidp_theme') !== null)

  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('vietidp_theme')
    if (saved) return saved
    // Respect system preference on first visit
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    // Only persist to localStorage if user manually chose
    if (manuallySet.current) {
      localStorage.setItem('vietidp_theme', theme)
    }
  }, [theme])

  // Listen to system theme changes (only if user hasn't manually toggled)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: light)')
    const handler = (e) => {
      if (!manuallySet.current) {
        setTheme(e.matches ? 'light' : 'dark')
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const toggleTheme = () => {
    manuallySet.current = true
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  const isDark = theme === 'dark'

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, isDark }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
