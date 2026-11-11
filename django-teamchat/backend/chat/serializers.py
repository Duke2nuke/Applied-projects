"""Serializers for the team-chat REST API."""

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Channel, Message, Reaction


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class ChannelSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = ["id", "name", "description", "created_at", "message_count"]

    def get_message_count(self, obj: Channel) -> int:
        return obj.messages.count()


class ReactionSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Reaction
        fields = ["id", "message", "user", "emoji", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.username", read_only=True)
    channel = serializers.CharField(source="channel.name", read_only=True)
    channel_id = serializers.IntegerField(source="channel.id", read_only=True)
    # Aggregated counts, e.g. {"👍": 2, "❤️": 1}. Read-only; reactions are
    # added through the reactions endpoint.
    reaction_counts = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "channel",
            "channel_id",
            "author",
            "content",
            "created_at",
            "reaction_counts",
        ]

    def get_reaction_counts(self, obj: Message) -> dict:
        counts: dict = {}
        for reaction in obj.reactions.all():
            counts[reaction.emoji] = counts.get(reaction.emoji, 0) + 1
        return counts
