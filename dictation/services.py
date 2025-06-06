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

def generate_audio_from_text(text, output_path):
    """
    Génère un fichier audio à partir du texte de la dictée en utilisant gTTS.
    
    Args:
        text (str): Le texte à convertir en audio
        output_path (str): Le chemin complet où sauvegarder le fichier audio
        
    Returns:
        str: L'URL Cloudinary du fichier audio
    """
    try:
        # S'assurer que le répertoire parent existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convertir le texte en audio avec gTTS
        tts = gTTS(text=text, lang='fr', slow=True)
        tts.save(output_path)
        
        logger.info(f"Audio généré localement : {output_path}")
        
        # Upload sur Cloudinary
        cloudinary_response = cloudinary.uploader.upload(
            output_path,
            resource_type="video",
            folder="dictations",
            public_id=os.path.basename(output_path).replace('.mp3', '')
        )
        
        # Supprimer le fichier local
        if os.path.exists(output_path):
            os.remove(output_path)
        
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
Tu es un professeur de français spécialiste de l'enseignement en Afrique de l'Ouest, notamment au Burkina Faso. Tu conçois des dictées vivantes et instructives pour des élèves burkinabè. Réponds UNIQUEMENT avec un OBJET JSON VALIDE. Ne donne aucun autre texte.

### Informations sur l'élève
- Âge : {age} ans
- Niveau scolaire : {niveau_scolaire}
- Objectif d'apprentissage : {objectif}
- Difficultés spécifiques à travailler : {difficultes}
- Durée estimée : {temps} minutes

### Objectif de la dictée

1. **Créer un petit récit cohérent, captivant et authentique**, inspiré d'un contexte africain (de préférence burkinabè).
2. Le récit doit se dérouler dans un **village, une ville ou une région du Burkina Faso**, ou faire référence à une **coutume locale, un animal de la savane, un métier traditionnel, une fête ou une scène de la vie quotidienne**.
3. Le texte doit intégrer un **savoir culturel ou lexical** : découverte d'un animal (ex : le fennec, le pangolin), d'un métier (ex : potier, forgeron), d'un lieu (ex : Bobo-Dioulasso, Gorom-Gorom), ou d'une pratique (ex : marché, cuisine, danse, masques, contes…).
4. Ajouter **au moins 3 mots peu fréquents ou spécifiques à la culture locale ou à la nature**, mais compréhensibles par le contexte.
5. Style fluide, phrases simples et syntaxe correcte, adaptées au niveau indiqué.
6. Répétition pédagogique :
   - Phrases **longues** (>10 mots) → **répétées 3 fois**
   - Phrases **courtes** (≤10 mots) → **répétées 2 fois**
   - Les répétitions doivent **sembler naturelles**, comme dans un conte ou un rappel narratif.
7. Ne surtout pas utiliser de formatage, retour à la ligne ou texte explicatif.

### Format OBLIGATOIRE de sortie
{{
  "text": "Texte intégral de la dictée avec répétitions intégrées dans un style fluide.",
  "title": "Titre court, en lien avec le thème culturel ou naturel burkinabè",
  "difficulty": "facile" // ou "moyenne" ou "difficile", selon le contenu généré
}}
"""
        
        # Génération de la dictée avec Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        # Validation et parsing de la réponse JSON
        try:
            # Nettoyage de la réponse pour s'assurer qu'elle est un JSON valide
            response_text = response.text.strip()
            if not response_text.startswith('{'):
                response_text = response_text[response_text.find('{'):]
            if not response_text.endswith('}'):
                response_text = response_text[:response_text.rfind('}')+1]
            
            result = json.loads(response_text)
            
            # Validation des champs requis
            required_fields = ['text', 'title', 'difficulty']
            if not all(field in result for field in required_fields):
                raise ValueError("Réponse JSON incomplète")
                
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON : {str(e)}")
            logger.error(f"Réponse brute de Gemini : {response.text}")
            return {"error": "Erreur de génération de la dictée"}
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la réponse : {str(e)}")
            return {"error": str(e)}
        
        # Création du dossier pour les dictées s'il n'existe pas
        dictations_dir = os.path.join(settings.MEDIA_ROOT, 'dictations')
        os.makedirs(dictations_dir, exist_ok=True)
        
        # Sauvegarde du texte dans un fichier JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = os.path.join(dictations_dir, f'dictation_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Génération de l'audio avec le chemin complet
        audio_path = os.path.join(dictations_dir, f'dictation_{timestamp}.mp3')
        audio_url = generate_audio_from_text(result['text'], audio_path)
        
        # Créer une nouvelle dictée dans la base de données
        from .models import Dictation
        dictation = Dictation.objects.create(
            title=result['title'],
            text=result['text'],
            difficulty=result['difficulty'],
            audio_file=f'dictations/dictation_{timestamp}.mp3'
        )
        
        return {
            'id': dictation.id,  # Utiliser l'ID réel de la base de données
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
        # Log pour déboguer
        logger.info(f"Texte reçu dans correct_dictation : {user_text}")
        logger.info(f"Type du texte : {type(user_text)}")
        logger.info(f"Longueur du texte : {len(user_text)}")
        logger.info(f"Texte après strip : {user_text.strip()}")
        logger.info(f"Longueur après strip : {len(user_text.strip())}")
        
        # Récupérer la dictée originale
        from .models import Dictation, DictationAttempt
        dictation = Dictation.objects.get(id=dictation_id)
        
        # Vérification STRICTE du texte vide
        if not user_text or not user_text.strip():
            logger.warning("Texte vide détecté")
            result = {
                'score': 0,
                'errors': [{
                    'word': '',
                    'correction': '',
                    'description': 'Le texte est vide. Veuillez écrire la dictée.'
                }],
                'correction': dictation.text,
                'total_words': len(dictation.text.split()),
                'error_count': len(dictation.text.split())
            }
            
            # Sauvegarder la tentative dans la base de données
            attempt = DictationAttempt.objects.create(
                dictation=dictation,
                user_text=user_text,
                score=0,
                feedback=json.dumps(result)
            )
            
            return {
                **result,
                'attempt_id': attempt.id
            }
        
        # Vérification de la longueur minimale
        if len(user_text.strip()) < len(dictation.text) * 0.1:
            logger.warning(f"Texte trop court : {len(user_text.strip())} < {len(dictation.text) * 0.1}")
            result = {
                'score': 0,
                'errors': [{
                    'word': '',
                    'correction': '',
                    'description': 'Le texte est trop court. Veuillez écrire la dictée complète.'
                }],
                'correction': dictation.text,
                'total_words': len(dictation.text.split()),
                'error_count': len(dictation.text.split())
            }
            
            # Sauvegarder la tentative dans la base de données
            attempt = DictationAttempt.objects.create(
                dictation=dictation,
                user_text=user_text,
                score=0,
                feedback=json.dumps(result)
            )
            
            return {
                **result,
                'attempt_id': attempt.id
            }
        
        # Configuration de Gemini
        genai.configure(api_key='AIzaSyDyCb6Lp9S-sOlMUMVrhwAHfeAiG6poQGI')
        model = genai.GenerativeModel('gemini-1.0-pro')
        
        # Prompt pour la correction
        prompt = f"""
Tu es un professeur de français expérimenté qui corrige les dictées d'élèves en Afrique francophone (Burkina Faso en particulier). Tu fais une correction juste, logique et bienveillante.

Voici le texte ORIGINAL de la dictée, exactement comme lu dans l'audio :

--- 
{dictation.text}
---

Et voici ce qu'a écrit l'élève :

---
{user_text}
---

Ta mission est de :
1. Comparer le texte de l'élève au texte original, non pas mot à mot, mais en tenant compte du **sens global**, du **contexte**, de la **syntaxe** et de la **logique grammaticale**.
2. Ne pénalise pas toute la suite du texte si l'élève a juste oublié ou ajouté un mot. Ne sois pas rigide : si l'élève a suivi le fil logique, conserve les points quand c'est justifié.
3. Identifie uniquement les **vraies erreurs** (orthographe, conjugaison, accord, ponctuation, grammaire).
4. Attribue une note sur 100 selon ce barème :
   - Mot clairement manquant : -5 points
   - Erreur d'orthographe : -2 points
   - Erreur de grammaire ou d'accord : -3 points
   - Erreur de ponctuation : -1 point
   - Mauvaise construction ou confusion sémantique : -3 points
   ⚠️ Si une erreur entraîne d'autres en chaîne, ne retire des points qu'une seule fois (pas de pénalité cumulative injuste).
5. Reconstitue le texte **corrigé**, exactement comme dans la dictée originale.
6. Garde une **approche pédagogique**, pas robotique.

Pour chaque erreur, fournis une description claire et pédagogique qui explique :
- Le type d'erreur (orthographe, grammaire, accord, ponctuation, mot manquant)
- La règle concernée
- Un conseil pour éviter cette erreur à l'avenir

Réponds uniquement avec un JSON strictement valide, au format suivant :
{{
  "score": <note sur 100>,
  "errors": [
    {{
      "word": "mot incorrect écrit par l'élève (ou vide si mot manquant)",
      "correction": "correction correcte",
      "description": "Description claire et pédagogique de l'erreur, incluant le type d'erreur, la règle et un conseil"
    }}
  ],
  "correction": "Texte corrigé exactement identique au texte dicté, sans fautes",
  "total_words": <nombre total de mots dans le texte original>,
  "error_count": <nombre total d'erreurs réelles détectées>
}}

IMPORTANT : 
- Pour les mots manquants, laisse "word" vide ("")
- Pour les erreurs d'orthographe, indique le mot tel qu'écrit par l'élève
- Pour les erreurs de grammaire/accord, indique le mot ou groupe de mots concerné
- Pour les erreurs de ponctuation, indique le signe de ponctuation concerné
- Pour les erreurs de construction, indique la phrase ou partie de phrase concernée

AUCUN texte supplémentaire. UNIQUEMENT le JSON. PAS d'explication ou commentaire autour.
"""
        
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