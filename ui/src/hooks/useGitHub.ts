import { useState, useCallback, useEffect } from 'react'
import { useAppStore } from '../store'
import type { GitHubUser, GitHubRepo } from '../types'

const GH_API = 'https://api.github.com'

// Module-level flag so auto-reconnect only fires once across all hook instances
let autoConnectAttempted = false

function ghHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: 'application/vnd.github.v3+json',
  }
}

export function useGitHub() {
  const { settings, updateSettings, githubUser, setGithubUser, githubRepos, setGithubRepos } =
    useAppStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const connect = useCallback(
    async (token: string) => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${GH_API}/user`, { headers: ghHeaders(token) })
        if (!res.ok) {
          throw new Error(res.status === 401 ? 'Invalid or expired token' : `GitHub error ${res.status}`)
        }
        const data = await res.json()
        const user: GitHubUser = { login: data.login, name: data.name, avatar_url: data.avatar_url }
        updateSettings({ githubToken: token })
        setGithubUser(user)
        return user
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to connect')
        return null
      } finally {
        setLoading(false)
      }
    },
    [updateSettings, setGithubUser]
  )

  // Auto-reconnect on app load if a token is persisted but the user session is lost
  useEffect(() => {
    const token = settings.githubToken
    if (!autoConnectAttempted && token && !githubUser) {
      autoConnectAttempted = true
      connect(token)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const disconnect = useCallback(() => {
    autoConnectAttempted = false
    updateSettings({ githubToken: '' })
    setGithubUser(null)
    setGithubRepos([])
  }, [updateSettings, setGithubUser, setGithubRepos])

  const fetchRepos = useCallback(async () => {
    const token = settings.githubToken
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const headers = ghHeaders(token)
      let all: GitHubRepo[] = []
      let page = 1
      while (page <= 10) {
        const res = await fetch(
          `${GH_API}/user/repos?per_page=100&page=${page}&sort=updated&affiliation=owner,collaborator,organization_member`,
          { headers }
        )
        if (!res.ok) throw new Error('Failed to fetch repositories')
        const data: GitHubRepo[] = await res.json()
        all = [...all, ...data]
        if (data.length < 100) break
        page++
      }
      setGithubRepos(all)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch repositories')
    } finally {
      setLoading(false)
    }
  }, [settings.githubToken, setGithubRepos])

  return {
    token: settings.githubToken,
    user: githubUser,
    repos: githubRepos,
    loading,
    error,
    connect,
    disconnect,
    fetchRepos,
    isConnected: !!settings.githubToken && !!githubUser,
  }
}
