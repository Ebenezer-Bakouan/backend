from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, Dictation, DictationAttempt,
    UserProgress, UserAchievement, UserFeedback
)
import logging

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    level = serializers.ChoiceField(
        choices=UserProfile._meta.get_field('level').choices,
        default='beginner'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'first_name', 'last_name', 'level']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Les mots de passe ne correspondent pas."})
        return data

    def create(self, validated_data):
        # Extraire le niveau et supprimer confirm_password
        level = validated_data.pop('level')
        validated_data.pop('confirm_password')
        
        # Créer l'utilisateur
        user = User.objects.create_user(**validated_data)
        
        # Créer le profil
        UserProfile.objects.create(user=user, level=level)
        
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'level', 'total_score', 'total_attempts', 'created_at', 'last_active']
        read_only_fields = ['id', 'total_score', 'total_attempts', 'created_at', 'last_active']

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