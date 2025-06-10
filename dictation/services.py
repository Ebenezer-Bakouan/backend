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
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("La clé API Gemini n'est pas configurée")
        genai.configure(api_key=api_key)
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
        configure_gemini_api()
        # Extraction des nouveaux paramètres
        age = params.get('age', '12')
        niveau_scolaire = params.get('niveauScolaire', 'Étudiant')
        objectif = params.get('objectifApprentissage', 'orthographe')
        difficultes = params.get('difficultesSpecifiques', '')
        temps = params.get('tempsDisponible', '10')
        niveau = params.get('niveau', 'facile')
        sujet = params.get('sujet', '')
        longueur = params.get('longueurTexte', '')
        type_contenu = params.get('typeContenu', '')
        vitesse = params.get('vitesseLecture', '')
        inclure_grammaire = params.get('includeGrammaire', False)
        inclure_conjugaison = params.get('includeConjugaison', False)
        inclure_orthographe = params.get('includeOrthographe', False)

        # Nouveau prompt enrichi
        prompt = f"""
Tu es un professeur de français expert, spécialisé dans la création de dictées pédagogiques culturelles pour des élèves burkinabè. Tu dois générer une dictée adaptée à un profil d’élève donné, sous forme d’un objet JSON enrichi, sans aucun retour à la ligne, balise ou symbole de formatage. Le texte doit être 100 % lisible et naturel.

## Profil de l'élève
- Âge : {age} ans
- Niveau scolaire : {niveau_scolaire}
- Objectif d'apprentissage : {objectif}
- Difficultés spécifiques : {difficultes or 'aucune'}
- Temps disponible : {temps} minutes

## Paramètres de la dictée
- Sujet imposé : {sujet or 'la vie au village'}
- Longueur souhaitée : {longueur or 'moyenne'}
- Niveau de difficulté : {niveau or 'moyen'}
- Type de contenu : {type_contenu or 'narratif'}
- Vitesse de lecture : {vitesse or 'normale'}
- Inclure orthographe complexe : {'oui' if inclure_orthographe else 'non'}
- Inclure conjugaisons difficiles : {'oui' if inclure_conjugaison else 'non'}
- Inclure accords grammaticaux : {'oui' if inclure_grammaire else 'non'}

## Contraintes de création
1. Respecte strictement le sujet imposé : \"{sujet or 'la vie au village'}\".
2. La longueur réelle du texte doit correspondre à :
   - Court : 3 à 4 phrases
   - Moyenne : 6 à 8 phrases
   - Long : 10 à 12 phrases ou plus
3. Chaque phrase de plus de 10 mots doit être répétée 3 fois, les plus courtes, 2 fois, naturellement.
4. Utilise un vocabulaire soutenu, culturellement situé (Burkina Faso), et évite toute simplification abusive.
5. Intègre au moins 3 mots rares, peu utilisés ou typiques du terroir burkinabè. Pas de glossaire.
6. Si demandé, inclure des conjugaisons complexes (imparfait, passé simple, conditionnel, etc.) et des accords grammaticaux exigeants.
7. Ne retourne AUCUN astérisque, tiret, retour à la ligne, ni balise HTML ou Markdown.
8. Retourne un objet JSON enrichi selon le format ci-dessous.

## Format de réponse JSON obligatoire
{{
  "title": "Un titre original et évocateur du thème choisi",
  "text": "Texte intégral de la dictée avec répétitions naturelles intégrées",
  "difficulty": "{niveau or 'moyen'}",
  "longueur_reelle": "{longueur or 'moyenne'}",
  "vocabulaire_rare": ["mot1", "mot2", "mot3"],
  "score_difficulte": un score entre 1 et 10 basé sur la richesse lexicale, syntaxique et les pièges orthographiques,
  "types_conjugaisons": ["passé simple", "imparfait", "futur"]  // si includeConjugaison,
  "accords_complexes": ["accord sujet-verbe inversé", "participe passé avec avoir"]  // si includeGrammaire
}}
"""
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        try:
            response_text = response.text.strip()
            if not response_text.startswith('{'):
                response_text = response_text[response_text.find('{'):]
            if not response_text.endswith('}'):
                response_text = response_text[:response_text.rfind('}')+1]
            result = json.loads(response_text)
            # Validation des champs requis (au moins ceux du format enrichi)
            required_fields = ['text', 'title', 'difficulty', 'longueur_reelle', 'vocabulaire_rare', 'score_difficulte']
            if not all(field in result for field in required_fields):
                raise ValueError("Réponse JSON enrichie incomplète")
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON : {str(e)}")
            logger.error(f"Réponse brute de Gemini : {response.text}")
            return {"error": "Erreur de génération de la dictée"}
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la réponse : {str(e)}")
            return {"error": str(e)}
        dictations_dir = os.path.join(settings.MEDIA_ROOT, 'dictations')
        os.makedirs(dictations_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = os.path.join(dictations_dir, f'dictation_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        audio_path = os.path.join(dictations_dir, f'dictation_{timestamp}.mp3')
        audio_url = generate_audio_from_text(result['text'], audio_path)
        from .models import Dictation
        dictation = Dictation.objects.create(
            title=result['title'],
            text=result['text'],
            difficulty=result['difficulty'],
            audio_file=f'dictations/dictation_{timestamp}.mp3'
        )
        # Structure enrichie en retour
        return {
            'id': dictation.id,
            'text': result['text'],
            'audio_url': audio_url,
            'title': result['title'],
            'difficulty': result['difficulty'],
            'longueur_reelle': result.get('longueur_reelle'),
            'vocabulaire_rare': result.get('vocabulaire_rare'),
            'score_difficulte': result.get('score_difficulte'),
            'types_conjugaisons': result.get('types_conjugaisons'),
            'accords_complexes': result.get('accords_complexes'),
        }
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la dictée : {str(e)}")
        return {"error": str(e)}

def clean_text_for_comparison(text: str) -> str:
    """
    Nettoie le texte pour une comparaison plus juste :
    - supprime les espaces en début/fin
    - remplace les espaces multiples par un seul
    - met en minuscules
    - supprime les caractères invisibles
    """
    import re
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    text = text.lower()
    text = text.replace('\u200b', '')  # caractères invisibles courants
    return text

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
        
        # Nettoyage des textes pour éviter les faux négatifs
        cleaned_user_text = clean_text_for_comparison(user_text)
        cleaned_dictation_text = clean_text_for_comparison(dictation.text)
        
        # Vérification STRICTE du texte vide
        if not cleaned_user_text:
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
        if len(cleaned_user_text) < len(cleaned_dictation_text) * 0.1:
            logger.warning(f"Texte trop court : {len(cleaned_user_text)} < {len(cleaned_dictation_text) * 0.1}")
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
        # Configuration de Gemini avec la clé depuis les paramètres
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("La clé API Gemini n'est pas configurée")
        genai.configure(api_key=api_key)
        
        # Utilisation du modèle Gemini adapté
        model = genai.GenerativeModel('gemini-pro')

        # Prompt pour la correction (utilise les textes nettoyés)
        prompt = f"""
Tu es un professeur de français expérimenté qui corrige les dictées d'élèves en Afrique francophone (Burkina Faso en particulier). Tu fais une correction juste, logique et bienveillante.

Voici le texte ORIGINAL de la dictée (nettoyé, sans casse ni espaces superflus) :
---
{cleaned_dictation_text}
---

Et voici ce qu'a écrit l'élève (nettoyé, sans casse ni espaces superflus) :
---
{cleaned_user_text}
---

Ta mission est de :
1. Comparer le texte de l'élève au texte original, non pas mot à mot, mais en tenant compte du **sens global**, du **contexte**, de la **syntaxe** et de la **logique grammaticale**.
2. Ne pénalise pas toute la suite du texte si l'élève a juste oublié ou ajouté un mot. Continue l'analyse avec un **alignement intelligent**.
3. Ignore les répétitions exactes de phrases. Ne les considère pas comme des fautes si elles suivent le sens dicté.
4. Accepte certaines tournures francophones locales tant qu'elles restent grammaticalement correctes et cohérentes.
5. Identifie uniquement les **vraies erreurs** (orthographe, conjugaison, accord, ponctuation, grammaire).
6. Attribue une note sur 100 selon ce barème :
   - Mot clairement manquant : -5 points
   - Erreur d'orthographe : -2 points
   - Erreur de grammaire ou d'accord : -3 points
   - Erreur de ponctuation : -1 point
   - Mauvaise construction ou confusion sémantique : -3 points
    Ne cumule pas les fautes en cascade : une seule pénalité par erreur source.
7. Reconstitue le texte **corrigé**, exactement comme dans la dictée originale, mais **sans les répétitions**.

Pour chaque erreur, fournis une description claire et pédagogique :
- Le type d'erreur (orthographe, grammaire, accord, ponctuation, mot manquant)
- La règle concernée
- Un conseil pour éviter cette erreur

Ajoute une section "Conseils pédagogiques" avec :
1. Résumé des erreurs fréquentes
2. Conseils pratiques pour s'améliorer
3. Exercices simples à faire

Exemple :
Texte original :
"le chien court dans le jardin."

Texte élève :
"le chie cour dan le jardin"

Réponse attendue :
{{
  "score": 92,
  "errors": [
    {{
      "word": "chie",
      "correction": "chien",
      "description": "Erreur d'orthographe : 'chie' est incorrect. Conseil : attention aux noms communs terminés en -ien."
    }},
    ...
  ],
  ...
}}

ATTENTION : Si tu ne réponds pas STRICTEMENT avec un objet JSON valide (et rien d'autre), la requête sera considérée comme échouée et tu seras pénalisé. Tu dois TOUJOURS répondre avec un objet JSON strictement valide, sans aucun texte autour, sans commentaire, sans markdown, sans explication, sans italique. Sinon, la correction sera rejetée.

Format OBLIGATOIRE :
{{
  "score": <note sur 100>,
  "errors": [
    {{
      "word": "...",
      "correction": "...",
      "description": "..."
    }}
  ],
  "correction": "Texte corrigé sans fautes et sans répétitions",
  "total_words": <nombre de mots dans le texte original>,
  "error_count": <nombre d'erreurs réelles détectées>,
  "pedagogical_advice": {{
    "summary": "...",
    "tips": ["...", "..."],
    "exercises": ["...", "..."]
  }}
}}

RAPPEL : Si tu ne respectes pas ce format JSON strict, ta réponse sera ignorée et tu seras pénalisé. Réponds uniquement avec l'objet JSON strictement valide.
"""
        # Génération de la correction avec Gemini
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        # Correction : extraire le JSON même s'il est entouré de texte ou de balises
        if '```json' in response_text:
            response_text = response_text.split('```json',1)[-1]
        if '```' in response_text:
            response_text = response_text.split('```',1)[0]
        response_text = response_text.strip()
        if not response_text.startswith('{'):
            response_text = response_text[response_text.find('{'):] if '{' in response_text else response_text
        if not response_text.endswith('}'): 
            response_text = response_text[:response_text.rfind('}')+1] if '}' in response_text else response_text
        if not response_text or not response_text.startswith('{'):
            logger.error(f"Réponse vide ou non JSON de Gemini : {response_text}")
            raise ValueError("La réponse de Gemini n'est pas un JSON valide.")
        correction_data = json.loads(response_text)
        # Correction : forcer la présence des champs attendus pour le front
        correction_data['correction'] = correction_data.get('correction', '') or ''
        correction_data['errors'] = [
            {
                'word': err.get('word', '') or '',
                'correction': err.get('correction', '') or '',
                'description': err.get('description', '') or ''
            } for err in correction_data.get('errors', [])
        ]
        # Sauvegarder la tentative dans la base de données
        attempt = Dict
            **correction_data,
            'attempt_id': attempt.id
        }
    except Exception as e:
        logger.error(f"Erreur lors de la correction de la dictée : {str(e)}")
        raise