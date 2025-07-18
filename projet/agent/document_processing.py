import json
from .mistral_client import request_mistral_model

def validate_and_summarize_document(query: str, subquery: str, document_content: str) -> dict:
    """
    Validates a document's relevance to a query/subquery and summarizes it using the Mistral model.

    Args:
        query: The initial broad research query.
        subquery: The specific sub-question the document is being evaluated against.
        document_content: The text content of the document to be analyzed.

    Returns:
        A dictionary with 'summary' (str or None) and 'is_relevant' (bool).
        Returns {"summary": None, "is_relevant": false} on error or if not relevant.
    """
    system_prompt = """Tu es un assistant de synthèse expert. Pour le texte que je te donne, tu dois effectuer deux tâches :
1.  Générer un résumé pertinent d'environ 150 mots.
2.  Évaluer sa pertinence par rapport à la question initiale ( est ce que le document repond a la question initiale ou peut aider a répondre a lquestion initiale avec l'aide d'autre document ).
Réponds uniquement avec un objet JSON strict.
Si le texte est pertinent, retourne : {"summary": "ton résumé ici", "is_relevant": true}.
Si le texte est hors sujet ou trop court, retourne : {"summary": null, "is_relevant": false}.
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",
         "content": f"""Question initiale : {query}\nSous-question : {subquery}\n\nTexte à analyser :\n{document_content}"""}
    ]

    try:
        response_json_str = request_mistral_model(messages)
        response_json_str = response_json_str.strip().strip('`').strip('json').strip()
        response_data = json.loads(response_json_str)
        return response_data
    except (json.JSONDecodeError, Exception) as e:
        print(f"❌ Erreur de format JSON ou de traitement lors de la validation du document : {e}")
        print("--- Réponse brute du modèle ---")
        print(response_json_str)
        print("------------------------------")
        return {"summary": None, "is_relevant": False}