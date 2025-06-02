from django.db import models

# Create your models here.

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

    def __str__(self):
        return self.title

class DictationAttempt(models.Model):
    dictation = models.ForeignKey(Dictation, on_delete=models.CASCADE, related_name='attempts')
    user_text = models.TextField()
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attempt on {self.dictation.title} - {self.created_at}"
