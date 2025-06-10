from rest_framework import serializers
from .models import (
    Dictation, DictationAttempt, UserFeedback
)

class DictationSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Dictation
        fields = [
            'id', 'title', 'text', 'difficulty', 'created_by',
            'created_at', 'audio_file', 'is_public', 'category', 'tags'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

class DictationAttemptSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    dictation = DictationSerializer(read_only=True)
    
    class Meta:
        model = DictationAttempt
        fields = [
            'id', 'dictation', 'user', 'user_text', 'score',
            'feedback', 'mistakes', 'time_taken', 'created_at', 'is_completed'
        ]
        read_only_fields = ['id', 'user', 'score', 'feedback', 'mistakes', 'created_at']

class UserProgressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    dictation = DictationSerializer(read_only=True)
    
    class Meta:
        model = UserProgress
        fields = [
            'id', 'user', 'dictation', 'best_score',
            'attempts_count', 'last_attempt', 'is_mastered'
        ]
        read_only_fields = ['id', 'user', 'dictation', 'last_attempt']

class UserAchievementSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = ['id', 'user', 'title', 'description', 'achieved_at', 'badge']
        read_only_fields = ['id', 'user', 'achieved_at']

class UserFeedbackSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    dictation = DictationSerializer(read_only=True)
    
    class Meta:
        model = UserFeedback
        fields = ['id', 'user', 'dictation', 'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'dictation', 'created_at']