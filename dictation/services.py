import os
import logging
import google.generativeai as genai
from datetime import datetime
from gtts import gTTS
import json
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings

# Configuration du logging
logger = logging.getLogger(__name__)

# Configuration de Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=settings.CLOUDINARY_STORAGE['API_KEY'],
    api_secret=settings.CLOUDINARY_STORAGE['API_SECRET']
)

def configure_gemini_api():
    """Configure l'API Gemini avec la clé API."""
    try:
        genai.configure(api_key='AIzaSyDyCb6Lp9S-sOlMUMVrhwAHfeAiG6poQGI')
        logger.info("Configuration de l'API Gemini réussie")
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de l'API Gemini : {str(e)}")
        raise

def generate_audio_from_text(text, output_dir='media/dictations'):
    """
    Génère un fichier audio à partir du texte de la dictée en utilisant gTTS et l'upload sur Cloudinary.
    
    Args:
        text (str): Le texte à convertir en audio
        output_dir (str): Le répertoire temporaire où sauvegarder le fichier audio
        
    Returns:
        str: L'URL Cloudinary du fichier audio
    """
    try:
        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(output_dir, exist_ok=True)
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        audio_filename = f'dictation_{timestamp}.mp3'
        audio_path = os.path.join(output_dir, audio_filename)
        
        # Convertir le texte en audio avec gTTS
        tts = gTTS(text=text, lang='fr', slow=True)
        tts.save(audio_path)
        
        logger.info(f"Audio généré localement : {audio_path}")
        
        # Upload sur Cloudinary
        cloudinary_response = cloudinary.uploader.upload(
            audio_path,
            resource_type="video",
            folder="dictations",
            public_id=audio_filename.replace('.mp3', '')
        )
        
        # Supprimer le fichier local
        os.remove(audio_path)
        
        logger.info(f"Audio uploadé sur Cloudinary : {cloudinary_response['secure_url']}")
        return cloudinary_response['secure_url']
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'audio : {str(e)}")
        raise

def generate_dictation(params):
    """
    Génère une dictée personnalisée en fonction des paramètres fournis.
    
    Args:
        params (dict): Dictionnaire contenant les paramètres de génération
        
    Returns:
        dict: Dictionnaire contenant le texte de la dictée et le chemin du fichier audio
    """
    try:
        # Configuration de l'API Gemini
        configure_gemini_api()
        
        # Extraction des paramètres
        age = params.get('age', '12')
        niveau_scolaire = params.get('niveauScolaire', 'Étudiant')
        objectif = params.get('objectifApprentissage', 'orthographe')
        difficultes = params.get('difficultesSpecifiques', '')
        temps = params.get('tempsDisponible', '10')
        
        # Construction du prompt pour Gemini
        prompt = f"""
        En tant que professeur de français, créez une dictée adaptée aux critères suivants :
        
        - Âge de l'élève : {age} ans
        - Niveau scolaire : {niveau_scolaire}
        - Objectif d'apprentissage : {objectif}
        - Difficultés spécifiques : {difficultes}
        - Durée estimée : {temps} minutes
        
        Règles importantes :
        1. Créez un texte COHÉRENT et NATUREL, comme un extrait de livre ou un article
        2. N'utilisez AUCUN marqueur de formatage (pas d'astérisques, de gras, d'italique, etc.)
        3. Le texte doit être fluide et agréable à écouter
        4. Incluez des mots qui correspondent à l'objectif d'apprentissage
        5. Adaptez la longueur et la complexité à l'âge et au niveau de l'élève
        6. Évitez les phrases trop longues ou complexes
        7. Utilisez un vocabulaire adapté au niveau scolaire
        8. IMPORTANT : Répétez chaque phrase longue (plus de 10 mots) 3 fois
        9. IMPORTANT : Répétez chaque phrase courte (10 mots ou moins) 2 fois
        
        Format de réponse souhaité :
        {{
            "text": "Le texte de la dictée, avec les répétitions des phrases. Exemple : 'Le chat dort. Le chat dort. La souris mange du fromage. La souris mange du fromage.'",
            "title": "Un titre court et descriptif",
            "difficulty": "facile/moyen/difficile"
        }}
        
        IMPORTANT : 
        - Le texte doit être parfaitement lisible et naturel
        - Répétez les phrases exactement de la même manière
        - Ne mettez pas de marqueurs ou d'indications de répétition
        """
        
        # Génération de la dictée avec Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        
        # Création du dossier pour les dictées s'il n'existe pas
        dictations_dir = os.path.join(settings.MEDIA_ROOT, 'dictations')
        os.makedirs(dictations_dir, exist_ok=True)
        
        # Sauvegarde du texte dans un fichier JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = os.path.join(dictations_dir, f'dictation_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Génération de l'audio
        audio_path = os.path.join(dictations_dir, f'dictation_{timestamp}.mp3')
        generate_audio_from_text(result['text'], audio_path)
        
        # Upload vers Cloudinary
        cloudinary_response = cloudinary.uploader.upload(
            audio_path,
            resource_type="video",
            folder="dictations",
            public_id=f"dictation_{timestamp}"
        )
        
        # Construction de l'URL Cloudinary
        audio_url = cloudinary_response['secure_url']
        
        # Nettoyage du fichier local
        os.remove(audio_path)
        
        return {
            'id': 14,  # ID temporaire
            'text': result['text'],
            'audio_url': audio_url,
            'title': result['title'],
            'difficulty': result['difficulty']
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la dictée : {str(e)}")
        return {"error": str(e)}

def correct_dictation(user_text: str, dictation_id: int) -> dict:
    """
    Corrige la dictée de l'utilisateur en utilisant Gemini.
    Retourne un dictionnaire contenant la note, les erreurs et la correction.
    """
    try:
        # Configuration de Gemini
        genai.configure(api_key='AIzaSyDyCb6Lp9S-sOlMUMVrhwAHfeAiG6poQGI')
        model = genai.GenerativeModel('gemini-pro')
        
        # Récupérer la dictée originale
        from .models import Dictation, DictationAttempt
        dictation = Dictation.objects.get(id=dictation_id)
        
        # Prompt pour la correction
        prompt = f"""Tu es un professeur de français qui corrige une dictée. 
        Voici le texte original :
        
        {dictation.text}
        
        Et voici le texte écrit par l'élève :
        
        {user_text}
        
        Ta tâche est de :
        1. Comparer ce texte avec la dictée originale
        2. Identifier toutes les erreurs (orthographe, grammaire, ponctuation)
        3. Attribuer une note sur 100 en fonction de la qualité du texte
        4. Fournir une liste détaillée des erreurs
        5. Fournir le texte corrigé
        
        Réponds au format JSON suivant :
        {{
            "score": <note sur 100>,
            "errors": [
                "Description de l'erreur 1",
                "Description de l'erreur 2",
                ...
            ],
            "correction": "Texte complet corrigé"
        }}
        
        IMPORTANT : Ne fournis QUE le JSON, sans commentaires ni explications supplémentaires."""
        
        # Génération de la correction avec Gemini
        response = model.generate_content(prompt)
        correction_data = json.loads(response.text)
        
        # Sauvegarder la tentative dans la base de données
        attempt = DictationAttempt.objects.create(
            dictation=dictation,
            user_text=user_text,
            score=correction_data['score'],
            feedback=json.dumps(correction_data)
        )
        
        return {
            **correction_data,
            'attempt_id': attempt.id
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la correction de la dictée : {str(e)}")
        raise 