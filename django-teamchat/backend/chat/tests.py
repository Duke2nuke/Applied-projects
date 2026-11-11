"""API tests for the team-chat proof project.

Run:  cd backend && ../.venv/bin/python manage.py test chat
Covers the five user-visible flows: login, channels, messages,
reactions (toggle), and search, plus the main validation errors.
"""

from django.test import TestCase
from rest_framework.test import APIClient


class TeamChatApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.post("/api/login/", {"username": "aarambh"}, format="json")
        channel = self.client.post(
            "/api/channels/",
            {"name": "general", "description": "Everyone starts here."},
            format="json",
        )
        assert channel.status_code == 201, channel.content
        self.channel_id = channel.data["id"]

    def _post_message(self, content, author="aarambh"):
        return self.client.post(
            f"/api/channels/{self.channel_id}/messages/",
            {"author": author, "content": content},
            format="json",
        )

    def test_login_creates_and_returns_user(self):
        response = self.client.post(
            "/api/login/", {"username": "meera"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "meera")
        # Logging in again returns the same user.
        again = self.client.post(
            "/api/login/", {"username": "meera"}, format="json"
        )
        self.assertEqual(again.data["id"], response.data["id"])

    def test_login_rejects_empty_username(self):
        response = self.client.post("/api/login/", {"username": "  "}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_and_list_channels(self):
        created = self.client.post(
            "/api/channels/", {"name": "django", "description": "Django talk."},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["message_count"], 0)
        listed = self.client.get("/api/channels/")
        names = [c["name"] for c in listed.data]
        self.assertEqual(names, ["django", "general"])  # ordered by name

    def test_duplicate_channel_name_rejected(self):
        response = self.client.post(
            "/api/channels/", {"name": "General"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_post_and_list_messages(self):
        posted = self._post_message("Hello Django team!")
        self.assertEqual(posted.status_code, 201)
        self.assertEqual(posted.data["author"], "aarambh")
        self.assertEqual(posted.data["channel"], "general")
        self.assertEqual(posted.data["reaction_counts"], {})
        listed = self.client.get(f"/api/channels/{self.channel_id}/messages/")
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(listed.data[0]["content"], "Hello Django team!")

    def test_post_message_rejects_empty_content(self):
        response = self._post_message("   ")
        self.assertEqual(response.status_code, 400)

    def test_post_message_to_missing_channel_is_404(self):
        response = self.client.post(
            "/api/channels/9999/messages/",
            {"author": "aarambh", "content": "hi"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_reaction_toggle_add_then_remove(self):
        message_id = self._post_message("React to this!").data["id"]
        added = self.client.post(
            f"/api/messages/{message_id}/reactions/",
            {"user": "aarambh", "emoji": "👍"},
            format="json",
        )
        self.assertEqual(added.status_code, 201)
        listed = self.client.get(f"/api/channels/{self.channel_id}/messages/")
        self.assertEqual(listed.data[0]["reaction_counts"], {"👍": 1})
        # Same reaction again removes it.
        removed = self.client.post(
            f"/api/messages/{message_id}/reactions/",
            {"user": "aarambh", "emoji": "👍"},
            format="json",
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.data["toggled"], "removed")
        listed = self.client.get(f"/api/channels/{self.channel_id}/messages/")
        self.assertEqual(listed.data[0]["reaction_counts"], {})

    def test_reaction_counts_aggregate_across_users(self):
        message_id = self._post_message("Two people like this.").data["id"]
        self.client.post(
            f"/api/messages/{message_id}/reactions/",
            {"user": "aarambh", "emoji": "👍"},
            format="json",
        )
        self.client.post(
            f"/api/messages/{message_id}/reactions/",
            {"user": "meera", "emoji": "👍"},
            format="json",
        )
        self.client.post(
            f"/api/messages/{message_id}/reactions/",
            {"user": "meera", "emoji": "❤️"},
            format="json",
        )
        listed = self.client.get(f"/api/channels/{self.channel_id}/messages/")
        self.assertEqual(listed.data[0]["reaction_counts"], {"👍": 2, "❤️": 1})

    def test_search_finds_by_content_and_author(self):
        self._post_message("Django models are fun")
        self._post_message("React components render fast", author="meera")
        found = self.client.get("/api/messages/", {"search": "django"})
        self.assertEqual(len(found.data), 1)
        self.assertEqual(found.data[0]["content"], "Django models are fun")
        by_author = self.client.get("/api/messages/", {"search": "meera"})
        self.assertEqual(len(by_author.data), 1)
        missing = self.client.get("/api/messages/", {"search": "flask"})
        self.assertEqual(len(missing.data), 0)
