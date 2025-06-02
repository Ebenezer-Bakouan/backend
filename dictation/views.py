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
    queryset = Dictation.objects.all()
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
            logger.info(f"Texte reçu : {user_text}")
            
            # Récupérer le texte original de la dernière dictée générée
            dictations_dir = os.path.join(settings.MEDIA_ROOT, 'dictations')
            latest_dictation = None
            latest_time = None
            
            for filename in os.listdir(dictations_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(dictations_dir, filename)
                    file_time = os.path.getmtime(file_path)
                    if latest_time is None or file_time > latest_time:
                        latest_time = file_time
                        latest_dictation = file_path
            
            if not latest_dictation:
                logger.error("Aucune dictée trouvée")
                return JsonResponse({'error': 'Aucune dictée trouvée'}, status=404)
            
            with open(latest_dictation, 'r', encoding='utf-8') as f:
                dictation_data = json.load(f)
                original_text = dictation_data.get('text', '').strip()
                logger.info(f"Texte original : {original_text}")

            # Utiliser Gemini pour corriger la dictée
            prompt = f"""
            En tant que professeur de français, corrigez cette dictée :

            Texte original : {original_text}
            Texte de l'élève : {user_text}

            Donnez votre réponse au format JSON suivant :
            {{
                "score": [note sur 100],
                "errors": [
                    "erreur 1",
                    "erreur 2",
                    ...
                ],
                "correction": "texte corrigé complet",
                "total_words": [nombre total de mots],
                "error_count": [nombre d'erreurs]
            }}

            Soyez précis dans la correction et expliquez clairement chaque erreur.
            """

            try:
                response = model.generate_content(prompt)
                result = json.loads(response.text)
                logger.info(f"Résultat de la correction : {result}")
                
                return JsonResponse({
                    'score': result['score'],
                    'errors': result['errors'],
                    'correction': result['correction'],
                    'total_words': result['total_words'],
                    'error_count': result['error_count']
                })
            except Exception as e:
                logger.error(f"Erreur Gemini : {str(e)}")
                # Fallback à la méthode simple si Gemini échoue
                user_words = user_text.lower().split()
                original_words = original_text.lower().split()
                
                errors = []
                for i, (user_word, original_word) in enumerate(zip(user_words, original_words)):
                    if user_word != original_word:
                        errors.append(f"Mot {i+1}: '{user_word}' au lieu de '{original_word}'")
                
                total_words = len(original_words)
                error_count = len(errors)
                score = max(0, 100 - (error_count * 5))
                
                return JsonResponse({
                    'score': score,
                    'errors': errors,
                    'correction': original_text,
                    'total_words': total_words,
                    'error_count': error_count
                })
            
        except Exception as e:
            logger.error(f"Erreur lors de la correction de la dictée : {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
