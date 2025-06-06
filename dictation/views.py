from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
import google.generativeai as genai
from gtts import gTTS
import os
from django.contrib.auth import get_user_model
from .models import (
    UserProfile, Dictation, DictationAttempt,
    UserProgress, UserAchievement, UserFeedback
)
from .serializers import (
    UserSerializer, UserProfileSerializer, DictationSerializer,
    DictationAttemptSerializer, UserProgressSerializer,
    UserAchievementSerializer, UserFeedbackSerializer,
    RegisterSerializer, LoginSerializer
)
from rest_framework.views import APIView
from .services import generate_dictation, correct_dictation
import logging
import urllib.parse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime
import difflib
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

User = get_user_model()

# Configuration du logging
logger = logging.getLogger(__name__)

# Configuration de l'API Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.0-pro')

class DictationViewSet(viewsets.ModelViewSet):
    queryset = Dictation.objects.all()
    serializer_class = DictationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Dictation.objects.filter(is_public=True)
        if self.request.user.is_authenticated:
            queryset |= Dictation.objects.filter(created_by=self.request.user)
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def attempt(self, request, pk=None):
        dictation = self.get_object()
        serializer = DictationAttemptSerializer(data=request.data)
        if serializer.is_valid():
            attempt = serializer.save(
                dictation=dictation,
                user=request.user
            )
            # Mise à jour du profil utilisateur
            profile = request.user.profile
            profile.total_attempts += 1
            if attempt.score:
                profile.total_score += attempt.score
            profile.save()
            
            # Mise à jour de la progression
            progress, created = UserProgress.objects.get_or_create(
                user=request.user,
                dictation=dictation
            )
            progress.attempts_count += 1
            if attempt.score and attempt.score > progress.best_score:
                progress.best_score = attempt.score
            progress.last_attempt = attempt.created_at
            progress.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def progress(self, request):
        progress = UserProgress.objects.filter(user=request.user)
        return Response(UserProgressSerializer(progress, many=True).data)

    @action(detail=False, methods=['get'])
    def achievements(self, request):
        achievements = UserAchievement.objects.filter(user=request.user)
        return Response(UserAchievementSerializer(achievements, many=True).data)

class UserFeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = UserFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserFeedback.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def generate_audio(self, request, pk=None):
        dictation = self.get_object()
        
        # Générer l'audio avec gTTS
        tts = gTTS(text=dictation.text, lang='fr')
        audio_path = os.path.join(settings.MEDIA_ROOT, 'dictations', f'dictation_{dictation.id}.mp3')
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        tts.save(audio_path)
        
        # Mettre à jour le chemin du fichier audio
        dictation.audio_file = f'dictations/dictation_{dictation.id}.mp3'
        dictation.save()
        
        return Response({'status': 'audio generated'})

    @action(detail=True, methods=['post'])
    def evaluate_attempt(self, request, pk=None):
        dictation = self.get_object()
        user_text = request.data.get('user_text')
        
        if not user_text:
            return Response({'error': 'user_text is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer une tentative
        attempt = DictationAttempt.objects.create(
            dictation=dictation,
            user_text=user_text
        )
        
        # Utiliser Gemini pour évaluer la dictée
        prompt = f"""
        Évaluez cette dictée :
        
        Texte original : {dictation.text}
        Texte de l'élève : {user_text}
        
        Donnez :
        1. Un score sur 100
        2. Une analyse détaillée des erreurs
        3. Des suggestions d'amélioration
        
        Format de réponse :
        Score : [score]/100
        Analyse : [analyse]
        Suggestions : [suggestions]
        """
        
        response = model.generate_content(prompt)
        evaluation = response.text
        
        # Extraire le score et le feedback
        try:
            score_line = evaluation.split('\n')[0]
            score = float(score_line.split(':')[1].strip().split('/')[0])
            feedback = '\n'.join(evaluation.split('\n')[1:])
        except:
            score = 0
            feedback = "Erreur lors de l'évaluation"
        
        # Mettre à jour la tentative
        attempt.score = score
        attempt.feedback = feedback
        attempt.save()
        
        return Response({
            'score': score,
            'feedback': feedback
        })

    @action(detail=True, methods=['get'])
    def attempts(self, request, pk=None):
        dictation = self.get_object()
        attempts = DictationAttempt.objects.filter(dictation=dictation).order_by('-created_at')
        serializer = DictationAttemptSerializer(attempts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        dictations = self.get_queryset()
        serializer = self.get_serializer(dictations, many=True)
        return Response(serializer.data)

class DictationAttemptViewSet(viewsets.ModelViewSet):
    queryset = DictationAttempt.objects.all().order_by('-created_at')
    serializer_class = DictationAttemptSerializer

    @action(detail=False, methods=['get'])
    def my_attempts(self, request):
        # Ici, vous pourriez filtrer par utilisateur quand l'authentification sera implémentée
        attempts = self.get_queryset()
        serializer = self.get_serializer(attempts, many=True)
        return Response(serializer.data)

class DictationView(APIView):
    def get(self, request):
        # Récupérer les paramètres de la requête
        params = request.query_params.dict()
        
        # Générer la dictée
        result = generate_dictation(params)
        
        if 'error' in result:
            return Response({'error': result['error']})
            
        # Si la requête demande le lecteur HTML
        if request.query_params.get('format') == 'html':
            return render(request, 'dictation_player.html', {
                'audio_files': [f'/media/{os.path.relpath(f, settings.MEDIA_ROOT)}' for f in result['audio_files']]
            })
            
        return Response(result)

class DictationViewSet(viewsets.ViewSet):
    def list(self, request):
        try:
            # Récupération et décodage des paramètres de la requête
            params = {}
            for key, value in request.query_params.items():
                # Décoder les valeurs URL-encoded
                decoded_value = urllib.parse.unquote(value)
                params[key] = decoded_value
            
            # Génération de la dictée
            result = generate_dictation(params)
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la dictée : {str(e)}")
            return Response(
                {"error": "Une erreur est survenue lors de la génération de la dictée"},
                status=500
            )

@csrf_exempt
def generate_dictation_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            result = generate_dictation(data)
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la dictée : {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def correct_dictation_view(request):
    logger.info("Début de la correction de la dictée")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_text = data.get('user_text', '').strip()
            dictation_id = data.get('dictation_id', 14)
            logger.info(f"Texte reçu : {user_text}")
            
            # Utiliser la fonction correct_dictation du service
            result = correct_dictation(user_text, dictation_id)
            logger.info(f"Résultat de la correction : {result}")
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la correction de la dictée : {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser
        })
