/** Typed fetch helpers for the Django API.
 *
 * Base URL defaults to the local Django dev server. Override with
 * VITE_API_URL (e.g. VITE_API_URL=http://localhost:8000/api npm run dev).
 */
import type { Channel, ChatMessage, User } from './types'

const API_BASE =
  import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      /* keep statusText */
    }
    throw new Error(`${res.status} ${detail}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  login(username: string): Promise<User> {
    return request<User>('/login/', {
      method: 'POST',
      body: JSON.stringify({ username }),
    })
  },
  listChannels(): Promise<Channel[]> {
    return request<Channel[]>('/channels/')
  },
  createChannel(name: string, description: string): Promise<Channel> {
    return request<Channel>('/channels/', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    })
  },
  listMessages(channelId: number): Promise<ChatMessage[]> {
    return request<ChatMessage[]>(`/channels/${channelId}/messages/`)
  },
  postMessage(
    channelId: number,
    author: string,
    content: string,
  ): Promise<ChatMessage> {
    return request<ChatMessage>(`/channels/${channelId}/messages/`, {
      method: 'POST',
      body: JSON.stringify({ author, content }),
    })
  },
  searchMessages(query: string, channelId?: number): Promise<ChatMessage[]> {
    const params = new URLSearchParams({ search: query })
    if (channelId) params.set('channel', String(channelId))
    return request<ChatMessage[]>(`/messages/?${params.toString()}`)
  },
  toggleReaction(
    messageId: number,
    user: string,
    emoji: string,
  ): Promise<unknown> {
    return request(`/messages/${messageId}/reactions/`, {
      method: 'POST',
      body: JSON.stringify({ user, emoji }),
    })
  },
}
