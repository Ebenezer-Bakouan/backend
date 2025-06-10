from django.db import models
from django.utils.translation import gettext_lazy as _

class Dictation(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Facile'),
        ('medium', 'Moyen'),
        ('hard', 'Difficile'),
    ]

    title = models.CharField(max_length=200)
    text = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    audio_file = models.FileField(upload_to='dictations/', null=True, blank=True)
    is_public = models.BooleanField(default=True)
    category = models.CharField(max_length=50, blank=True)
    tags = models.CharField(max_length=200, blank=True)  # Stocké comme une chaîne séparée par des virgules

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

class DictationAttempt(models.Model):
    dictation = models.ForeignKey(Dictation, on_delete=models.CASCADE, related_name='attempts')
    user_text = models.TextField()
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)
    mistakes = models.JSONField(null=True, blank=True)
    time_taken = models.IntegerField(null=True, blank=True)  # Time taken in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Attempt for {self.dictation.title}"

    class Meta:
        ordering = ['-created_at']
