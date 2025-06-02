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
        vitesse_lecture = params.get('vitesseLecture', 'normale') # Ce paramètre ne sera plus utilisé pour gTTS
        
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
        
        # Génération du texte avec Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        dictation_text = response.text.strip()
        
        # Nettoyer le texte des astérisques pour l'audio et construire la chaîne audio avec répétitions
        audio_parts = []
        
        # Tenter d'extraire le titre et le texte principal
        lines = dictation_text.split('\n', 1)
        title = ""
        main_text = dictation_text
        
        if len(lines) > 0 and lines[0].strip().startswith('**Dictée :'):
             # Nettoyer le titre des astérisques pour l'audio
            title = lines[0].strip().replace('*', '').replace('Dictée :', '').strip()
            main_text = lines[1].strip() if len(lines) > 1 else ""
            audio_parts.append(f"Dictée : {title}.")
            audio_parts.append(" ....\n") # Petite pause après le titre
            
        elif len(lines) > 0 and lines[0].strip().startswith('Dictée :'):
             # Nettoyer le titre pour l'audio
            title = lines[0].strip().replace('Dictée :', '').strip()
            main_text = lines[1].strip() if len(lines) > 1 else ""
            audio_parts.append(f"Dictée : {title}.")
            audio_parts.append(" ....\n") # Petite pause après le titre
        
        text_to_split = main_text.replace('*', '').strip()
        
        # Diviser le texte principal en phrases (logique simplifiée)
        sentences = []
        current_sentence = ""
        separators = ['. ', '! ', '? ', '... ', '.\n', '!\n', '?\n']

        i = 0
        while i < len(text_to_split):
            found_separator = False
            for sep in separators:
                if text_to_split[i:i+len(sep)] == sep:
                    if current_sentence.strip():
                        sentences.append(current_sentence.strip() + sep.strip())
                    current_sentence = ""
                    i += len(sep)
                    found_separator = True
                    break
            if not found_separator:
                current_sentence += text_to_split[i]
                i += 1

        if current_sentence.strip():
            sentences.append(current_sentence.strip())
            
        # Construire la chaîne audio avec répétitions et pauses
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            words = sentence.split()
            repetitions = 3 if len(words) > 15 else 2 # 3 répétitions si longue, 2 sinon
            
            repeated_sentence = (' ... ' if repetitions > 1 else '').join([sentence.strip()] * repetitions)
            audio_parts.append(repeated_sentence)
            audio_parts.append(" ....\n") # Pause plus longue entre les phrases

        audio_text = " ".join(audio_parts).strip()
        
        # Génération de l'audio (fichier unique avec gTTS)
        audio_files = generate_audio_from_text(audio_text)
        
        return {
            'text': dictation_text, # Retourne le texte original avec formatage
            'audio_files': audio_files
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la dictée : {str(e)}")
        raise 

def correct_dictation(user_text: str) -> dict:
    """
    Corrige la dictée de l'utilisateur en utilisant Gemini.
    Retourne un dictionnaire contenant la note, les erreurs et la correction.
    """
    try:
        # Configuration de Gemini
        genai.configure(api_key='AIzaSyDyCb6Lp9S-sOlMUMVrhwAHfeAiG6poQGI')
        model = genai.GenerativeModel('gemini-pro')
        
        # Prompt pour la correction
        prompt = f"""Tu es un professeur de français qui corrige une dictée. 
        Voici le texte écrit par l'élève :
        
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
        
        return correction_data
        
    except Exception as e:
        logger.error(f"Erreur lors de la correction de la dictée : {str(e)}")
        raise 