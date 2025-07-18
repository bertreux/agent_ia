import json
from .mistral_client import request_mistral_model

def validate_final_synthesis(query: str, synthesis: str, documents: list[dict]) -> dict:
    """
    Validates the coherence and relevance of the final synthesis against its source documents.

    Args:
        query: The initial research query.
        synthesis: The generated final synthesis text.
        documents: A list of dictionaries, where each dictionary represents a source document
                   (e.g., with 'url', 'title', 'summary').

    Returns:
        A dictionary with 'is_coherent' (bool) and 'reason' (str).
    """
    system_prompt = """Tu es un assistant de validation d'information expert.
    Ta mission est d'évaluer la qualité d'une synthèse en la comparant aux documents sources qui ont servi à la générer.
    Réponds uniquement avec un objet JSON strict.
    La synthèse peut parler d'autre chose tant que c'est en rapport avec la question initiale et que la question initiale est répondue dans la synthese.
    Si la synthèse est pertinente et ne contient pas d'informations qui ne sont pas dans les documents sources, retourne : {"is_coherent": true, "reason": "La synthèse est cohérente."}.
    Si la synthèse est incohérente, qu'elle "hallucine" ou qu'elle ne répond pas à la question, retourne : {"is_coherent": false, "reason": "Explique pourquoi la synthèse n'est pas cohérente ou pertinente."}.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",
         "content": f"""Question initiale : {query}\n\nSynthèse à valider : {synthesis}\n\nDocuments sources : {json.dumps(documents, ensure_ascii=False)}"""}
    ]
    try:
        response_json_str = request_mistral_model(messages)
        response_json_str = response_json_str.strip().strip('`').strip('json').strip()
        return json.loads(response_json_str)
    except (json.JSONDecodeError, Exception) as e:
        print(f"❌ Erreur de format JSON ou de traitement lors de la validation finale : {e}")
        print("--- Réponse brute du modèle ---")
        print(response_json_str)
        print("------------------------------")
        return {"is_coherent": False, "reason": "Erreur de format ou de traitement de la réponse de validation."}