import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { get, postJSON } from './api'

const MeContext = createContext(null)

export function MeProvider({ children }) {
  const [me, setMe] = useState(null) // null = loading
  const [unread, setUnread] = useState(0)

  const refresh = useCallback(() => get('/api/me').then(setMe).catch(() => setMe({ logged_in: false })), [])

  // Keyed on which user is signed in, not merely whether someone is: switching
  // accounts without a page reload must refetch, or the badge shows the
  // previous user's count.
  const refreshUnread = useCallback(() => {
    if (!me?.orcid) { setUnread(0); return Promise.resolve() }
    return get('/api/notifications').then((r) => setUnread(r.unread)).catch(() => {})
  }, [me?.orcid])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => { refreshUnread() }, [refreshUnread])

  const logout = useCallback(async () => {
    await postJSON('/auth/logout', {})
    refresh()
  }, [refresh])

  return (
    <MeContext.Provider value={{ me, refresh, logout, unread, refreshUnread }}>
      {children}
    </MeContext.Provider>
  )
}

export const useMe = () => useContext(MeContext)
