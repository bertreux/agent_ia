import os
import json
import argparse
from mistralai import Mistral
from selenium_util import scrape_worker_threaded
from google_search import fetch_search_results_with_googlesearch
from config import model, max_thread, max_synth_retries, max_retry_document
from concurrent.futures import ThreadPoolExecutor

def parse_args():
    parser = argparse.ArgumentParser(description="Recherche profonde avec sélection et synthèse")
    parser.add_argument("query", help="Question ou sujet à rechercher")
    parser.add_argument("-n", "--n_results", type=int, default=5,
                        help="Nombre de résultats Google à récupérer par sous-question")
    parser.add_argument("-k", "--k_pick", type=int, default=3, help="Nombre de sous-questions à générer")
    return parser.parse_args()

def request_model(messages):
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    resp = client.chat.complete(
        model=os.environ.get("MODEL", model),
        messages=messages,
    )
    raw_content = resp.choices[0].message.content.strip()
    return raw_content

def generate_subqueries(query, k):
    system_msg = {
        "role": "system",
        "content": "Tu es un assistant expert en recherche documentaire."
    }
    user_msg = {
        "role": "user",
        "content": (
            f"Pour la question suivante :\n\n'{query}'\n\n"
            f"Merci de générer exactement {k} sous-questions différentes, précises et pertinentes "
            "pour explorer ce sujet en profondeur. "
            "Réponds uniquement par une liste numérotée, sans aucune explication ni introduction, de cette forme :\n"
            "1. Première sous-question\n2. Deuxième...\n3. Troisième...\n"
        )
    }
    messages = [system_msg, user_msg]
    raw_text = request_model(messages)
    subqueries = []
    for line in raw_text.splitlines():
        line = line.strip()
        if line.startswith(tuple(f"{i}." for i in range(1, k + 1))):
            parts = line.split(".", 1)
            if len(parts) > 1:
                subqueries.append(parts[1].strip())
    if len(subqueries) < k:
        print(f"⚠️ Seulement {len(subqueries)} sous-questions extraites sur {k} attendues.")
        print("Réponse brute :", raw_text)
        subqueries = [query] * k
    return subqueries

def validate_synthesis(query, synthesis, documents):
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
        response_json_str = request_model(messages)
        response_json_str = response_json_str.strip().strip('`').strip('json').strip()
        return json.loads(response_json_str)
    except (json.JSONDecodeError, Exception) as e:
        print(f"❌ Erreur de format JSON ou de traitement lors de la validation : {e}")
        print("--- Réponse brute du modèle ---")
        print(response_json_str)
        print("------------------------------")
        return {"is_coherent": False, "reason": "Erreur de format ou de traitement de la réponse de validation."}

def deep_research(query, n_results, k_pick, progress_callback=None):
    if progress_callback is None:
        progress_callback = lambda p, s: None # Default do-nothing callback

    max_global_retries = 3
    global_retry_count = 0
    final_result = None

    while global_retry_count < max_global_retries:
        print(f"\n--- Début de la tentative de recherche globale n°{global_retry_count + 1}/{max_global_retries} ---")
        progress_callback(5, "🧠 Génération des sous-recherches par l'IA...")
        subqueries = generate_subqueries(query, k_pick)
        print("💡 Sous-recherches générées :")
        for i, sq in enumerate(subqueries, 1):
            print(f"({i}) {sq}")
        print()

        documents_by_subq = {sq: [] for sq in subqueries}
        visited_urls = set()
        tasks = []

        progress_callback(20, "🔍 Récupération des URLs pour chaque sous-question...")
        for i, subq in enumerate(subqueries, 1):
            results_to_fetch = n_results + 3
            all_results = fetch_search_results_with_googlesearch(subq, results_to_fetch)
            urls_collected = 0
            print(f"URLs récupérées pour sous-question {i} :")
            for title, url in all_results:
                if urls_collected >= n_results:
                    break
                if url not in visited_urls:
                    print(f"  {urls_collected + 1}. {url}")
                    tasks.append({"url": url, "subquestion": subq})
                    visited_urls.add(url)
                    urls_collected += 1
                else:
                    print(f"  {urls_collected + 1}. {url} (Ignoré - doublon)")
        print()

        if not tasks:
            print("❌ Aucune URL valide à scraper. Tentative suivante...")
            global_retry_count += 1
            continue # Restart the while loop for a new global retry

        max_workers = min(len(tasks), max_thread)
        progress_callback(40, f"🚀 Démarrage du scraping en parallèle avec {max_workers} threads...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(scrape_worker_threaded, task) for task in tasks]
            for future in futures:
                result = future.result()
                if result:
                    documents_by_subq[result['subquestion']].append(result)

        print("\n🧾 Contenu extrait depuis les sites :")
        doc_count = 1
        for subq, docs in documents_by_subq.items():
            for doc in docs:
                print(f"--- Document {doc_count} ---")
                print(f"🔗 URL : {doc.get('url')}")
                print(f"❓ Sous-question : {doc.get('subquestion')}")
                print(f"🏷️ Titre : {doc.get('title')}")
                print("📄 Contenu extrait :")
                print(doc.get("paragraphs", "")[:500])
                print("----------------------\n")
                doc_count += 1

        progress_callback(60, "✂️ Pré-résumé et validation des documents avec l'IA...")
        validated_summaries = []

        for subq_idx, subq in enumerate(subqueries):
            progress_callback(60 + int(20 * (subq_idx / len(subqueries))), f"✂️ Traitement de la sous-question : {subq}")
            print(f"\n--- Traitement de la sous-question : {subq} ---")
            relevant_docs = []
            subq_retries = 0

            initial_docs = documents_by_subq.get(subq, [])
            for doc in initial_docs:
                if len(relevant_docs) >= n_results:
                    break

                if len(doc.get("paragraphs", "")) > 100:
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
                         "content": f"""Question initiale : {query}\nSous-question : {subq}\n\nTexte à analyser :\n{doc.get('paragraphs')}"""}
                    ]
                    try:
                        response_json_str = request_model(messages)
                        response_json_str = response_json_str.strip().strip('`').strip('json').strip()
                        response_data = json.loads(response_json_str)

                        if response_data.get("is_relevant", False):
                            relevant_docs.append({
                                "url": doc.get("url"),
                                "subquestion": doc.get("subquestion"),
                                "title": doc.get("title"),
                                "summary": response_data.get("summary")
                            })
                            print(f"✅ Document pertinent trouvé : {doc.get('url')}")
                        else:
                            print(f"⚠️ Document de {doc.get('url')} jugé non pertinent.")

                    except (json.JSONDecodeError, Exception) as e:
                        print(f"❌ Erreur de format JSON ou de traitement pour {doc.get('url')} : {e}")
                        print("--- Réponse brute du modèle ---")
                        print(response_json_str)
                        print("------------------------------")
                else:
                    if doc.get("paragraphs", "").strip():
                        relevant_docs.append({
                            "url": doc.get("url"),
                            "subquestion": doc.get("subquestion"),
                            "title": doc.get("title"),
                            "summary": doc.get("paragraphs")
                        })
                        print(f"✅ Document court mais pertinent trouvé : {doc.get('url')}")
                    else:
                        print(f"⚠️ Document de {doc.get('url')} est vide. Ignoré.")

            while len(relevant_docs) < n_results and subq_retries < max_retry_document:
                print(
                    f"♻️ Nombre de documents pertinents insuffisant pour '{subq}'. Recherche d'une URL de remplacement (tentative {subq_retries + 1}/{max_retry_document})...")

                new_results_to_check = fetch_search_results_with_googlesearch(subq, 10)

                new_url_found = False
                for new_title, new_url in new_results_to_check:
                    if new_url not in visited_urls:
                        print(f"✅ Nouvelle URL de remplacement trouvée : {new_url}")
                        visited_urls.add(new_url)
                        new_url_found = True

                        new_task = {"url": new_url, "subquestion": subq}
                        new_doc = scrape_worker_threaded(new_task)

                        if new_doc and len(new_doc.get("paragraphs", "")) > 100:
                            try:
                                messages = [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user",
                                     "content": f"""Question initiale : {query}\nSous-question : {subq}\n\nTexte à analyser :\n{new_doc.get('paragraphs')}"""}
                                ]
                                response_json_str = request_model(messages)
                                response_json_str = response_json_str.strip().strip('`').strip('json').strip()
                                response_data = json.loads(response_json_str)
                                if response_data.get("is_relevant", False):
                                    relevant_docs.append({
                                        "url": new_doc.get("url"),
                                        "subquestion": new_doc.get("subquestion"),
                                        "title": new_doc.get("title"),
                                        "summary": response_data.get("summary")
                                    })
                                    print(f"✅ Document de remplacement pertinent trouvé et ajouté.")
                                else:
                                    print(f"⚠️ Document de {new_doc.get('url')} jugé non pertinent.")
                            except Exception as e:
                                print(f"❌ Erreur de traitement du document de remplacement : {e}.")
                        else:
                            print(f"⚠️ Document de remplacement vide ou trop court. Ignoré.")

                        break

                if not new_url_found:
                    print("❌ Aucune nouvelle URL valide à ajouter. Arrêt de la recherche de remplacement pour cette sous-question.")
                    break

                subq_retries += 1

            validated_summaries.extend(relevant_docs)

        if not validated_summaries:
            print(f"\n❌ La validation des documents n'a pas abouti pour cette tentative. (Tentative {global_retry_count + 1}/{max_global_retries}). Redémarrage de la recherche...")
            global_retry_count += 1
            continue # Restart the while loop for a new global retry

        progress_callback(85, "🤖 Synthèse finale avec l'IA...")
        synth = None
        attempt = 0
        while synth is None and attempt < max_synth_retries:
            attempt += 1
            print(f"Tentative de synthèse n°{attempt}/{max_synth_retries}...")
            synth_msgs = [
                {"role": "system",
                 "content": "Tu es un assistant de synthèse expert. Tu vas synthétiser les informations contenues dans les résumés pertinents fournis pour répondre à la question initiale. Utilise les URLs comme références. Et ne met pas de partie de reference."},
                {"role": "user", "content": json.dumps({"query": query, "data": validated_summaries}, ensure_ascii=False)}
            ]
            synth_content = request_model(synth_msgs)

            print("\n✂️ Étape 4 : vérification de la cohérence de la synthèse...")
            validation_result = validate_synthesis(query, synth_content, validated_summaries)

            if validation_result.get("is_coherent", False):
                print("✅ La synthèse est cohérente et valide.")
                synth = synth_content
            else:
                print(f"⚠️ La synthèse est jugée incohérente. Raison : {validation_result.get('reason')}")
                if attempt < max_synth_retries:
                    print("♻️ Nouvelle tentative de synthèse...")
                else:
                    print("❌ Nombre maximal de tentatives de synthèse atteint. Renvoie de la derniere synthese.")
                    synth = synth_content # Return the last synthesis, even if incoherent for final review
                    break # Exit inner while loop

        if synth: # If a synthesis was successfully generated (coherent or last attempt)
            sources_by_subquery = []
            for sq in subqueries:
                urls = [doc["url"] for doc in validated_summaries if doc.get("subquestion") == sq]
                sources_by_subquery.append({
                    "subquestion": sq,
                    "urls": urls
                })
            final_result = {
                "synthèse": synth,
                "sous_questions": subqueries,
                "sources": sources_by_subquery,
            }
            progress_callback(100, "✅ Recherche terminée !")
            return final_result # Successfully completed, exit the global retry loop

        else: # If synth is None (meaning no valid synthesis after max_synth_retries)
            print(f"\n❌ La synthèse finale a échoué après {max_synth_retries} tentatives. (Tentative globale {global_retry_count + 1}/{max_global_retries}). Redémarrage de la recherche...")
            global_retry_count += 1
            continue # Restart the while loop for a new global retry

    # If we reach here, all global retries have been exhausted without a successful result
    print("\n❌ Toutes les tentatives de recherche globale ont échoué.")
    progress_callback(100, "❌ Recherche échouée après plusieurs tentatives.")
    return final_result # Return the last attempt's result, which might be None or an incoherent synthesis

def main():
    args = parse_args()
    if "MISTRAL_API_KEY" not in os.environ:
        print("❌ La variable MISTRAL_API_KEY doit être définie.")
        exit(1)
    answer = deep_research(args.query, args.n_results, args.k_pick)
    if answer:
        print("\n🧠 Synthèse finale :\n", answer["synthèse"])
        print("\n🔎 Sous-questions explorées :")
        for sq in answer["sous_questions"]:
            print(f"- {sq}")
        print("\n🔗 Sources utilisées :")
        for source_group in answer["sources"]:
            print(f"  - Pour '{source_group['subquestion']}':")
            for url in source_group['urls']:
                print(f"    - {url}")
    else:
        print("\n❌ Aucune réponse valide n'a pu être générée après plusieurs tentatives.")

if __name__ == "__main__":
    main()
