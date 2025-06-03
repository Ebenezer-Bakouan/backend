from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
import google.generativeai as genai
from gtts import gTTS
import os
from .models import Dictation, DictationAttempt
from .serializers import DictationSerializer, DictationAttemptSerializer
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

# Configuration du logging
logger = logging.getLogger(__name__)

# Configuration de l'API Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.0-pro')

class DictationViewSet(viewsets.ModelViewSet):
    queryset = Dictation.objects.all().order_by('-created_at')
    serializer_class = DictationSerializer

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
            user_text = data.get('text', '').strip()
            dictation_id = data.get('dictation_id', 14)  # Utiliser l'ID de la dictée
            logger.info(f"Texte reçu : {user_text}")
            
            # Utiliser la fonction correct_dictation du service
            result = correct_dictation(user_text, dictation_id)
            logger.info(f"Résultat de la correction : {result}")
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la correction de la dictée : {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
