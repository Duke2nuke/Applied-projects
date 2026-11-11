from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login, name="login"),
    path("users/", views.user_list, name="user-list"),
    path("channels/", views.channel_list, name="channel-list"),
    path("channels/<int:channel_id>/", views.channel_detail, name="channel-detail"),
    path(
        "channels/<int:channel_id>/messages/",
        views.channel_messages,
        name="channel-messages",
    ),
    path("messages/", views.message_search, name="message-search"),
    path(
        "messages/<int:message_id>/reactions/",
        views.message_reactions,
        name="message-reactions",
    ),
]
