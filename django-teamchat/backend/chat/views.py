"""Views for the team-chat REST API.

No auth tokens: clients send a plain ``username`` with each write
("simple login" — see ``login`` below). That is a deliberate
local-demo simplification for this proof project, not a production
design. Reads are open; writes validate their inputs and return
400/404 rather than crashing.
"""

from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Channel, Message, Reaction
from .serializers import (
    ChannelSerializer,
    MessageSerializer,
    ReactionSerializer,
    UserSerializer,
)


def _get_or_create_user(username):
    """Return (user, error_response). Username must be 1-40 chars."""
    if not isinstance(username, str) or not username.strip():
        return None, Response(
            {"detail": "username is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    username = username.strip()
    if len(username) > 40:
        return None, Response(
            {"detail": "username must be at most 40 characters."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user, _ = User.objects.get_or_create(username=username)
    return user, None


@api_view(["POST"])
def login(request):
    """Simple login: POST {"username": "aarambh"} -> {"id": 1, "username": ...}.

    Creates the user on first use. No password is set or checked.
    """
    user, error = _get_or_create_user(request.data.get("username"))
    if error is not None:
        return error
    return Response(UserSerializer(user).data)


@api_view(["GET", "POST"])
def channel_list(request):
    if request.method == "GET":
        channels = Channel.objects.all()
        return Response(ChannelSerializer(channels, many=True).data)

    name = (request.data.get("name") or "").strip()
    if not name:
        return Response(
            {"detail": "name is required."}, status=status.HTTP_400_BAD_REQUEST
        )
    if Channel.objects.filter(name__iexact=name).exists():
        return Response(
            {"detail": f"Channel #{name} already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    channel = Channel.objects.create(
        name=name, description=(request.data.get("description") or "").strip()
    )
    return Response(ChannelSerializer(channel).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def channel_detail(request, channel_id):
    channel = get_object_or_404(Channel, pk=channel_id)
    return Response(ChannelSerializer(channel).data)


@api_view(["GET", "POST"])
def channel_messages(request, channel_id):
    channel = get_object_or_404(Channel, pk=channel_id)
    if request.method == "GET":
        messages = (
            channel.messages.select_related("author")
            .prefetch_related("reactions")
            .all()
        )
        return Response(MessageSerializer(messages, many=True).data)

    content = (request.data.get("content") or "").strip()
    if not content:
        return Response(
            {"detail": "content is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    author, error = _get_or_create_user(request.data.get("author"))
    if error is not None:
        return error
    message = Message.objects.create(
        channel=channel, author=author, content=content
    )
    return Response(
        MessageSerializer(message).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def message_search(request):
    """Search messages by content: GET /api/messages/?search=django.

    Optional ``channel`` query param filters to one channel id.
    An empty search returns all messages (newest last, capped at 100).
    """
    query = (request.GET.get("search") or "").strip()
    messages = Message.objects.select_related("author", "channel").prefetch_related(
        "reactions"
    )
    channel_id = request.GET.get("channel")
    if channel_id:
        messages = messages.filter(channel_id=channel_id)
    if query:
        messages = messages.filter(
            Q(content__icontains=query) | Q(author__username__icontains=query)
        )
    return Response(MessageSerializer(messages[:100], many=True).data)


@api_view(["GET", "POST"])
def message_reactions(request, message_id):
    message = get_object_or_404(Message, pk=message_id)
    if request.method == "GET":
        return Response(
            ReactionSerializer(message.reactions.all(), many=True).data
        )

    emoji = (request.data.get("emoji") or "").strip()
    if not emoji or len(emoji) > 8:
        return Response(
            {"detail": "emoji is required (at most 8 characters)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user, error = _get_or_create_user(request.data.get("user"))
    if error is not None:
        return error
    # Toggle: posting the same reaction again removes it.
    existing = Reaction.objects.filter(
        message=message, user=user, emoji=emoji
    ).first()
    if existing is not None:
        existing.delete()
        return Response(
            {"detail": "reaction removed.", "toggled": "removed"},
            status=status.HTTP_200_OK,
        )
    reaction = Reaction.objects.create(message=message, user=user, emoji=emoji)
    return Response(
        ReactionSerializer(reaction).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
def user_list(request):
    return Response(UserSerializer(User.objects.all(), many=True).data)
