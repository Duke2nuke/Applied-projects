/** Types matching the Django REST API (backend/chat/serializers.py). */

export interface Channel {
  id: number
  name: string
  description: string
  created_at: string
  message_count: number
}

export interface ChatMessage {
  id: number
  channel: string
  channel_id: number
  author: string
  content: string
  created_at: string
  reaction_counts: Record<string, number>
}

export interface User {
  id: number
  username: string
}

export const REACTION_EMOJIS = ['👍', '❤️', '🎉'] as const
