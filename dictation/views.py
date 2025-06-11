from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.conf import settings
import google.generativeai as genai
from gtts import gTTS
import os
from .models import Dictation, DictationAttempt
from .serializers import DictationSerializer, DictationAttemptSerializer
from .services import generate_dictation, correct_dictation
import logging
import urllib.parse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime
import difflib
from itertools import zip_longest
import base64
import io
from PIL import Image
import pytesseract
import openai

# Configuration du logging
logger = logging.getLogger(__name__)

# Configuration de l'API Gemini
logger.info("Configuration de l'API Gemini")
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.0-pro')
    logger.info("API Gemini configurée avec succès")
except Exception as e:
    logger.error(f"Erreur lors de la configuration de l'API Gemini : {str(e)}")
    logger.exception("Trace complète de l'erreur de configuration Gemini :")

class DictationViewSet(viewsets.ModelViewSet):
    queryset = Dictation.objects.filter(is_public=True)
    serializer_class = DictationSerializer

    @action(detail=True, methods=['post'])
    def attempt(self, request, pk=None):
        dictation = self.get_object()
        serializer = DictationAttemptSerializer(data=request.data)
        if serializer.is_valid():
            attempt = serializer.save(dictation=dictation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

@api_view(['POST'])
def correct_dictation_view(request):
    """
    Corrige une dictée soumise de façon pédagogique (alignement intelligent, feedback détaillé).
    """
    try:
        dictation_id = request.data.get('dictation_id')
        user_text = request.data.get('user_text', '').strip()
        
        if not dictation_id:
            return Response({'error': 'ID de dictée manquant'}, status=status.HTTP_400_BAD_REQUEST)
        if not user_text:
            return Response({'error': 'Le texte de la dictée est vide'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            dictation_id = int(dictation_id)
        except (ValueError, TypeError) as e:
            return Response({'error': f'ID de dictée invalide: {dictation_id}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Correction pédagogique via le service
        try:
            result = correct_dictation(user_text, dictation_id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'Erreur lors de la correction: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': f'Erreur lors de la correction de la dictée: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def generate_dictation_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            result = generate_dictation(data)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@api_view(['POST'])
def process_image(request):
    try:
        # Get base64 image from request
        image_data = request.data.get('image')
        if not image_data:
            return Response({'error': 'No image data provided'}, status=400)

        # Remove data URL prefix if present
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]

        # Convert base64 to image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # Extract text from image using Tesseract OCR
        extracted_text = pytesseract.image_to_string(image, lang='fra')

        # Use OpenAI to correct the text
        corrected_text = correct_text_with_ai(extracted_text)

        return Response({
            'text': corrected_text,
            'original_text': extracted_text
        })

    except Exception as e:
        return Response({'error': str(e)}, status=500)

def correct_text_with_ai(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un assistant spécialisé dans la correction de textes en français. Corrige les erreurs d'orthographe et de grammaire dans le texte suivant tout en conservant son sens original."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        print(f"Error correcting text with AI: {str(e)}")
        return text  # Return original text if AI correction fails

@api_view(['POST'])
def process_image_gemini(request):
    try:
        # Get base64 image from request
        image_data = request.data.get('image')
        if not image_data:
            return Response({'error': 'Aucune image fournie'}, status=400)

        # Remove data URL prefix if present
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]

        # Préparer le prompt
        prompt = """Tu es un expert en reconnaissance de texte manuscrit en français.
        Examine l'image fournie et extrait exactement le texte que tu y vois.
        Retourne uniquement le texte extrait, sans commentaires ni formatage."""

        # Préparer la requête pour l'API Gemini
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    }
                ]
            }]
        }

        try:
            import requests
            response = requests.post(
                api_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code != 200:
                logger.error(f"Erreur Gemini API: {response.text}")
                raise Exception(f"Erreur API: {response.status_code}")
                
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            
            # Retourner le résultat
            return Response({
                "texte_extrait": text
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de l'image avec Gemini : {str(e)}")
            return Response({
                'error': "Erreur lors de l'analyse de l'image. Veuillez réessayer."
            }, status=500)

    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'image : {str(e)}")
        return Response({
            'error': "Une erreur inattendue s'est produite. Veuillez réessayer."
        }, status=500)
