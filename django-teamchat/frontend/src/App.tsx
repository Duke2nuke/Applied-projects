import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import { REACTION_EMOJIS, type Channel, type ChatMessage } from './types'

const STORED_USER_KEY = 'teamchat-username'

export default function App() {
  const [username, setUsername] = useState<string>(
    () => localStorage.getItem(STORED_USER_KEY) ?? '',
  )
  const [loginInput, setLoginInput] = useState('')
  const [channels, setChannels] = useState<Channel[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [search, setSearch] = useState('')
  const [compose, setCompose] = useState('')
  const [newChannel, setNewChannel] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const selected = channels.find((c) => c.id === selectedId) ?? null

  const loadChannels = useCallback(async () => {
    const list = await api.listChannels()
    setChannels(list)
    if (selectedId === null && list.length > 0) setSelectedId(list[0].id)
    return list
  }, [selectedId])

  const loadMessages = useCallback(async (channelId: number) => {
    setMessages(await api.listMessages(channelId))
  }, [])

  // Load channels once logged in.
  useEffect(() => {
    if (!username) return
    setLoading(true)
    loadChannels()
      .catch((e: Error) => setError(`Could not load channels: ${e.message}`))
      .finally(() => setLoading(false))
  }, [username, loadChannels])

  // Load the thread whenever the selected channel changes.
  useEffect(() => {
    if (selectedId === null) return
    setSearch('')
    loadMessages(selectedId).catch((e: Error) =>
      setError(`Could not load messages: ${e.message}`),
    )
  }, [selectedId, loadMessages])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    const name = loginInput.trim()
    if (!name) return
    try {
      const user = await api.login(name)
      localStorage.setItem(STORED_USER_KEY, user.username)
      setUsername(user.username)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    }
  }

  async function handleCreateChannel(e: React.FormEvent) {
    e.preventDefault()
    const name = newChannel.trim()
    if (!name) return
    try {
      const created = await api.createChannel(name, '')
      setNewChannel('')
      const list = await loadChannels()
      setSelectedId(created.id)
      setChannels(list)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create channel')
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault()
    if (selectedId === null || !compose.trim()) return
    try {
      const posted = await api.postMessage(selectedId, username, compose.trim())
      setMessages((prev) => [...prev, posted])
      setCompose('')
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send message')
    }
  }

  async function handleReact(message: ChatMessage, emoji: string) {
    try {
      await api.toggleReaction(message.id, username, emoji)
      if (selectedId !== null) await loadMessages(selectedId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not react')
    }
  }

  async function handleSearch(query: string) {
    setSearch(query)
    if (selectedId === null) return
    try {
      if (!query.trim()) {
        await loadMessages(selectedId)
      } else {
        setMessages(await api.searchMessages(query.trim(), selectedId))
      }
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    }
  }

  if (!username) {
    return (
      <main className="login">
        <h1>TeamChat</h1>
        <p>A small Django + React team chat. Pick a username to join.</p>
        <form onSubmit={handleLogin}>
          <input
            aria-label="Username"
            value={loginInput}
            onChange={(e) => setLoginInput(e.target.value)}
            placeholder="Your username"
          />
          <button type="submit">Join</button>
        </form>
        {error && <p className="error">{error}</p>}
      </main>
    )
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>TeamChat</h1>
        <p className="me">Signed in as {username}</p>
        <h2>Channels</h2>
        {loading && <p>Loading channels…</p>}
        <ul>
          {channels.map((c) => (
            <li key={c.id}>
              <button
                className={c.id === selectedId ? 'active' : ''}
                onClick={() => setSelectedId(c.id)}
              >
                #{c.name} ({c.message_count})
              </button>
            </li>
          ))}
        </ul>
        <form onSubmit={handleCreateChannel}>
          <input
            aria-label="New channel name"
            value={newChannel}
            onChange={(e) => setNewChannel(e.target.value)}
            placeholder="New channel name"
          />
          <button type="submit">Create channel</button>
        </form>
      </aside>

      <main className="thread">
        <header>
          <h2>{selected ? `#${selected.name}` : 'Pick a channel'}</h2>
          {selected?.description && <p>{selected.description}</p>}
          <input
            aria-label="Search messages"
            value={search}
            onChange={(e) => void handleSearch(e.target.value)}
            placeholder="Search messages in this channel…"
          />
        </header>

        {error && <p className="error">{error}</p>}

        <ul className="messages">
          {messages.map((m) => (
            <li key={m.id} className="message">
              <strong>{m.author}</strong>{' '}
              <span className="time">
                {new Date(m.created_at).toLocaleString()}
              </span>
              <p>{m.content}</p>
              <div className="reactions">
                {REACTION_EMOJIS.map((emoji) => (
                  <button
                    key={emoji}
                    onClick={() => void handleReact(m, emoji)}
                    aria-label={`React ${emoji} to message ${m.id}`}
                  >
                    {emoji} {m.reaction_counts[emoji] ?? 0}
                  </button>
                ))}
              </div>
            </li>
          ))}
          {messages.length === 0 && <li>No messages yet. Say hello!</li>}
        </ul>

        <form onSubmit={handleSend} className="compose">
          <input
            aria-label="Message"
            value={compose}
            onChange={(e) => setCompose(e.target.value)}
            placeholder={`Message #${selected?.name ?? ''}`}
            disabled={selectedId === null}
          />
          <button type="submit" disabled={selectedId === null}>
            Send
          </button>
        </form>
      </main>
    </div>
  )
}
