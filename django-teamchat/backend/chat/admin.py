from django.contrib import admin

from .models import Channel, Message, Reaction

admin.site.register(Channel)
admin.site.register(Message)
admin.site.register(Reaction)
