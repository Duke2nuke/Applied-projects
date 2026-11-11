"""Models for the team-chat proof project.

Small on purpose: a Channel (a stream/topic room), a Message in a
channel, and a Reaction on a message. Users are Django's built-in
User model; the API "logs in" by username only (no password) — see
chat/views.py. That is a deliberate local-demo simplification, not a
production auth design.
"""

from django.contrib.auth.models import User
from django.db import models

#: Emojis the UI offers. The API accepts any short emoji string, but the
#: frontend only sends these three.
REACTION_EMOJIS = ("👍", "❤️", "🎉")


class Channel(models.Model):
    """A chat room, like a Zulip stream/channel."""

    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"#{self.name}"


class Message(models.Model):
    """One message posted by a user into a channel."""

    channel = models.ForeignKey(
        Channel, related_name="messages", on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        User, related_name="messages", on_delete=models.CASCADE
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.author.username} in #{self.channel.name}: {self.content[:40]}"


class Reaction(models.Model):
    """One user's emoji reaction on one message.

    One row per (message, user, emoji); posting the same reaction twice
    removes it again (toggle), handled in the view.
    """

    message = models.ForeignKey(
        Message, related_name="reactions", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, related_name="reactions", on_delete=models.CASCADE
    )
    emoji = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "emoji"],
                name="unique_message_user_emoji",
            )
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.user.username} {self.emoji} on message {self.message_id}"
