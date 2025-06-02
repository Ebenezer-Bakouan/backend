def generate_dictation_prompt(params):
    """
    Génère un prompt pour l'API Gemini qui créera une dictée adaptée aux paramètres fournis.
    """
    prompt = f"""Crée une dictée en français avec les caractéristiques suivantes :
- Niveau : {params.get('niveau', 'moyen')}
- Âge : {params.get('age', '15')} ans
- Niveau scolaire : {params.get('niveauScolaire', 'Étudiant')}
- Objectif d'apprentissage : {params.get('objectifApprentissage', 'accord')}
- Difficultés spécifiques : {params.get('difficultesSpecifiques', 'homophone')}
- Temps disponible : {params.get('tempsDisponible', '15')} minutes
- Sujet : {params.get('sujet', 'animaux')}
- Longueur du texte : {params.get('longueurTexte', 'moyen')}
- Type de contenu : {params.get('typeContenu', 'narratif')}
- Vitesse de lecture : {params.get('vitesseLecture', 'normale')}

Instructions spécifiques :
1. Crée UNIQUEMENT le texte de la dictée, sans introduction ni conclusion
2. Le texte doit être cohérent et adapté au niveau spécifié
3. Inclure les points grammaticaux demandés de manière naturelle
4. Éviter les phrases trop longues ou complexes
5. Utiliser un vocabulaire approprié au niveau scolaire
6. Le texte doit être facilement dictable

Format de réponse souhaité :
[Texte de la dictée uniquement, sans numérotation ni marqueurs]"""

    return prompt 