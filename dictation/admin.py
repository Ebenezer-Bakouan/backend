from django.contrib import admin
from .models import Dictation, DictationAttempt

@admin.register(Dictation)
class DictationAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'created_at')
    list_filter = ('difficulty', 'created_at')
    search_fields = ('title', 'text')

@admin.register(DictationAttempt)
class DictationAttemptAdmin(admin.ModelAdmin):
    list_display = ('dictation', 'score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user_text', 'feedback')
