import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { get, postJSON } from './api'

const MeContext = createContext(null)

export function MeProvider({ children }) {
  const [me, setMe] = useState(null) // null = loading

  const refresh = useCallback(() => get('/api/me').then(setMe).catch(() => setMe({ logged_in: false })), [])

  useEffect(() => { refresh() }, [refresh])

  const logout = useCallback(async () => {
    await postJSON('/auth/logout', {})
    refresh()
  }, [refresh])

  return <MeContext.Provider value={{ me, refresh, logout }}>{children}</MeContext.Provider>
}

export const useMe = () => useContext(MeContext)
