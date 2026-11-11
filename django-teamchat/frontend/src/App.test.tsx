/** Frontend smoke test: the app renders the login screen, then (with a
 * mocked API) the channel list and a message thread with reactions.
 * Run: npm test
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const channels = [
  {
    id: 1,
    name: 'general',
    description: 'Everyone starts here.',
    created_at: '2026-11-11T00:00:00Z',
    message_count: 1,
  },
  {
    id: 2,
    name: 'django',
    description: 'Django backend talk.',
    created_at: '2026-11-11T00:00:00Z',
    message_count: 0,
  },
]

const messages = [
  {
    id: 1,
    channel: 'general',
    channel_id: 1,
    author: 'aarambh',
    content: 'Hello Django team!',
    created_at: '2026-11-11T00:00:00Z',
    reaction_counts: { '👍': 1 },
  },
]

function mockFetch(url: string) {
  const body = url.includes('/login/')
    ? { id: 1, username: 'aarambh' }
    : url.includes('/messages/')
      ? messages
      : channels
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
  })
}

describe('TeamChat App', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn(mockFetch))
  })

  it('shows the login screen first', () => {
    render(<App />)
    expect(screen.getByText('TeamChat')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Join' })).toBeInTheDocument()
  })

  it('loads channels and the message thread after login', async () => {
    render(<App />)
    fireEvent.change(screen.getByLabelText('Username'), {
      target: { value: 'aarambh' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Join' }))

    expect(await screen.findByText('#general (1)')).toBeInTheDocument()
    expect(screen.getByText('#django (0)')).toBeInTheDocument()
    expect(await screen.findByText('Hello Django team!')).toBeInTheDocument()
    expect(screen.getByText('👍 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Search messages')).toBeInTheDocument()
    expect(screen.getByLabelText('Message')).toBeInTheDocument()
    expect(screen.getByLabelText('New channel name')).toBeInTheDocument()
  })
})
