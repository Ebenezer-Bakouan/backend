from rest_framework import serializers
from .models import Dictation, DictationAttempt

class DictationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dictation
        fields = [
            'id', 'title', 'text', 'difficulty',
            'created_at', 'audio_file', 'is_public', 'category', 'tags'
        ]
        read_only_fields = ['id', 'created_at']

class DictationAttemptSerializer(serializers.ModelSerializer):
    dictation = DictationSerializer(read_only=True)
    
    class Meta:
        model = DictationAttempt
        fields = [
            'id', 'dictation', 'user_text', 'score',
            'feedback', 'mistakes', 'time_taken', 'created_at', 'is_completed'
        ]
        read_only_fields = ['id', 'score', 'feedback', 'mistakes', 'created_at']