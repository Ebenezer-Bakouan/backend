import os
import logging
import google.generativeai as genai
from datetime import datetime
from gtts import gTTS # Revenir à gTTS
import json

# Configuration du logging
logger = logging.getLogger(__name__)

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
    Génère un fichier audio unique à partir du texte de la dictée en utilisant gTTS.
    
    Args:
        text (str): Le texte à convertir en audio
        output_dir (str): Le répertoire où sauvegarder le fichier audio
        
    Returns:
        list: Liste contenant le chemin du fichier audio généré
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
        
        logger.info(f"Audio généré : {audio_path}")
        return [audio_path]
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'audio : {str(e)}")
        return []

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
        
        # Récupération des paramètres
        age = params.get('age', 15)
        niveau_scolaire = params.get('niveauScolaire', 'Étudiant')
        objectif = params.get('objectifApprentissage', 'accord')
        difficultes = params.get('difficultesSpecifiques', 'homophone')
        temps = params.get('tempsDisponible', 15)
        niveau = params.get('niveau', 'moyen')
        sujet = params.get('sujet', 'animaux')
        longueur = params.get('longueurTexte', 'moyen')
        type_contenu = params.get('typeContenu', 'narratif')
        
        # Construction du prompt
        prompt = f"""Génère une dictée en français avec les caractéristiques suivantes :
        - Niveau : {niveau} (adapté à un {niveau_scolaire} de {age} ans)
        - Objectif d'apprentissage : {objectif}
        - Difficultés spécifiques à travailler : {difficultes}
        - Durée : {temps} minutes
        - Sujet : {sujet}
        - Longueur : {longueur}
        - Type de contenu : {type_contenu}
        
        La dictée doit être :
        - Adaptée au niveau spécifié
        - Claire et bien structurée
        - Intéressante et engageante
        - Avec une ponctuation appropriée
        - Sans explications supplémentaires
        
        IMPORTANT : Ne fournis QUE le texte de la dictée, sans commentaires ni explications. Le texte DOIT commencer par 'Dictée : [Un titre adapté] ' suivi du texte de la dictée."""

        # Génération de la dictée avec Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        dictation_text = response.text.strip()

        # Génération de l'audio
        audio_files = generate_audio_from_text(dictation_text)
        logger.info(f"Fichiers audio générés : {audio_files}")
        
        # Sauvegarder la dictée dans la base de données
        from .models import Dictation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f'dictations/dictation_{timestamp}.mp3'
        
        dictation = Dictation.objects.create(
            title=f"Dictée sur {sujet}",
            text=dictation_text,
            difficulty=niveau,
            audio_file=audio_filename
        )
        
        # Construire l'URL Cloudinary
        cloudinary_url = f"https://res.cloudinary.com/dlrudclbm/video/upload/{audio_filename}"
        logger.info(f"URL Cloudinary générée : {cloudinary_url}")
        
        return {
            'id': dictation.id,
            'text': dictation_text,
            'audio_url': cloudinary_url,
            'title': dictation.title,
            'difficulty': dictation.difficulty
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la dictée : {str(e)}")
        raise

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