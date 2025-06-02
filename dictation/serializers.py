from rest_framework import serializers
from .models import Dictation, DictationAttempt

class DictationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dictation
        fields = ['id', 'title', 'text', 'difficulty', 'created_at', 'audio_file']

class DictationAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DictationAttempt
        fields = ['id', 'dictation', 'user_text', 'score', 'feedback', 'created_at']
        read_only_fields = ['score', 'feedback'] 