"""Seed demo data: python manage.py seed_demo

Creates 3 users, 3 channels, and a handful of messages + reactions.
Safe to re-run: it clears existing chat data first. Local demo only.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from chat.models import Channel, Message, Reaction


class Command(BaseCommand):
    help = "Seed the team-chat demo with users, channels, messages, reactions."

    def handle(self, *args, **options):
        Reaction.objects.all().delete()
        Message.objects.all().delete()
        Channel.objects.all().delete()
        User.objects.filter(username__in=["aarambh", "meera", "dev"]).delete()

        users = {
            name: User.objects.create_user(username=name)
            for name in ["aarambh", "meera", "dev"]
        }
        channels = {
            name: Channel.objects.create(name=name, description=desc)
            for name, desc in [
                ("general", "Everyone starts here."),
                ("django", "Django backend talk: models, views, DRF."),
                ("react", "React frontend talk: components, hooks, TypeScript."),
            ]
        }
        seed_messages = [
            ("general", "aarambh", "Welcome to TeamChat — a small Django + React team chat."),
            ("general", "meera", "Hi everyone! First message in #general."),
            ("django", "aarambh", "Models are in chat/models.py: Channel, Message, Reaction."),
            ("django", "dev", "The API is plain DRF, no auth tokens — simple login by username."),
            ("django", "meera", "Search works too: try /api/messages/?search=django"),
            ("react", "aarambh", "The frontend is React + TypeScript with Vite."),
            ("react", "dev", "Channel list on the left, thread in the middle, compose box below."),
        ]
        messages = []
        for channel_name, author, content in seed_messages:
            messages.append(
                Message.objects.create(
                    channel=channels[channel_name],
                    author=users[author],
                    content=content,
                )
            )
        Reaction.objects.create(message=messages[0], user=users["meera"], emoji="👍")
        Reaction.objects.create(message=messages[0], user=users["dev"], emoji="🎉")
        Reaction.objects.create(message=messages[2], user=users["meera"], emoji="❤️")
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded 3 users, 3 channels, "
                f"{len(messages)} messages, 3 reactions."
            )
        )
