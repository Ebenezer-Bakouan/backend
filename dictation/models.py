from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Débutant'),
            ('intermediate', 'Intermédiaire'),
            ('advanced', 'Avancé'),
            ('expert', 'Expert')
        ],
        default='beginner'
    )
    total_score = models.IntegerField(default=0)
    total_attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

class Dictation(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Facile'),
        ('medium', 'Moyen'),
        ('hard', 'Difficile'),
    ]

    title = models.CharField(max_length=200)
    text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_dictations')
    created_at = models.DateTimeField(auto_now_add=True)
    audio_file = models.FileField(upload_to='dictations/', null=True, blank=True)
    is_public = models.BooleanField(default=True)
    category = models.CharField(max_length=50, blank=True)
    tags = models.CharField(max_length=200, blank=True)  # Stocké comme une chaîne séparée par des virgules

    def __str__(self):
        return self.title

class DictationAttempt(models.Model):
    dictation = models.ForeignKey(Dictation, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attempts', null=True, blank=True)
    user_text = models.TextField()
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    mistakes = models.JSONField(null=True, blank=True)  # Stocke les erreurs détaillées
    time_taken = models.IntegerField(null=True, blank=True)  # Temps en secondes
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'}'s attempt on {self.dictation.title}"

class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    dictation = models.ForeignKey(Dictation, on_delete=models.CASCADE, related_name='user_progress')
    best_score = models.FloatField(default=0)
    attempts_count = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(null=True, blank=True)
    is_mastered = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'dictation']

    def __str__(self):
        return f"{self.user.username}'s progress on {self.dictation.title}"

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=100)
    description = models.TextField()
    achieved_at = models.DateTimeField(auto_now_add=True)
    badge = models.ImageField(upload_to='achievements/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class UserFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    dictation = models.ForeignKey(Dictation, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'dictation']

    def __str__(self):
        return f"{self.user.username}'s feedback on {self.dictation.title}"
