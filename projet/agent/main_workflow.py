import json
from concurrent.futures import ThreadPoolExecutor

# Use relative imports for modules within the same package
from .selenium_util import scrape_worker_threaded
from .google_search import fetch_search_results_with_googlesearch
from .config import max_thread, max_synth_retries, max_retry_document

# Corrected imports for other modules within the agent package
from .mistral_client import request_mistral_model
from .document_processing import validate_and_summarize_document
from .validation_synthesis import validate_final_synthesis

# --- Global Configuration/State (mimicking parts of the class for clarity) ---
ALL_STEPS = [
    "Préparation de la recherche",
    "Génération des sous-recherches par l'IA",
    "Récupération des URLs pour chaque sous-question",
    "Scraping des contenus des pages web",
    "Pré-résumé et validation des documents avec l'IA",
    "Validation de la pertinence des documents",
    "Recherche de documents de remplacement (si nécessaire)",
    "Synthèse finale avec l'IA",
    "Vérification de la cohérence de la synthèse",
    "Recherche terminée"
]
TOTAL_STEPS = len(ALL_STEPS)


def generate_subqueries_for_ui(query: str, k_pick: int, progress_callback) -> list[str]:
    """
    Generates subqueries and returns them to the UI.

    Args:
        query: The main research query.
        k_pick: The desired number of subqueries.
        progress_callback: A function to update the UI's progress.

    Returns:
        A list of generated subqueries.
    """
    current_step_idx = 1
    progress_callback(5, ALL_STEPS[current_step_idx], current_step_idx)

    system_msg = {
        "role": "system",
        "content": "Tu es un assistant expert en recherche documentaire."
    }
    user_msg = {
        "role": "user",
        "content": (
            f"Pour la question suivante :\n\n'{query}'\n\n"
            f"Merci de générer exactement {k_pick} sous-questions différentes, précises et pertinentes "
            "pour explorer ce sujet en profondeur. "
            "Réponds uniquement par une liste numérotée, sans aucune explication ni introduction, de cette forme :\n"
            "1. Première sous-question\n2. Deuxième...\n3. Troisième...\n"
        )
    }
    messages = [system_msg, user_msg]
    raw_text = request_mistral_model(messages)
    subqueries = []
    for line in raw_text.splitlines():
        line = line.strip()
        if line.startswith(tuple(f"{i}." for i in range(1, k_pick + 1))):
            parts = line.split(".", 1)
            if len(parts) > 1:
                subqueries.append(parts[1].strip())
    if len(subqueries) < k_pick:
        print(f"⚠️ Seulement {len(subqueries)} sous-questions extraites sur {k_pick} attendues.")
        print("Réponse brute :", raw_text)
        subqueries = [query] * k_pick
    else:
        subqueries = subqueries[:k_pick]


    print("💡 Sous-recherches générées :")
    for i, sq in enumerate(subqueries, 1):
        print(f"({i}) {sq}")
    return subqueries


def _fetch_and_scrape_urls(subqueries: list[str], n_results: int, visited_urls: set, progress_callback) -> dict:
    """
    Fetches search results and scrapes content from unique URLs for each subquery.

    Args:
        subqueries: A list of sub-questions.
        n_results: The desired number of results per subquery.
        visited_urls: A set of URLs already visited to avoid duplicates.
        progress_callback: A function to update the UI's progress.

    Returns:
        A dictionary mapping subqueries to lists of scraped document data.
    """
    current_step_idx = 2
    progress_callback(20, ALL_STEPS[current_step_idx], current_step_idx)

    tasks = []
    documents_by_subq = {sq: [] for sq in subqueries}

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
        raise Exception("❌ Aucune URL valide à scraper.")

    current_step_idx = 3
    max_workers = min(len(tasks), max_thread)
    progress_callback(40, ALL_STEPS[current_step_idx], current_step_idx)

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
    return documents_by_subq


def _process_documents(query: str, subqueries: list[str], documents_by_subq: dict, n_results: int, visited_urls: set,
                       progress_callback, max_new_url_attempts: int = 5) -> list[dict]:
    """
    Processes scraped documents by validating their relevance and summarizing them.
    Also handles replacement document search if initial documents are insufficient.

    Args:
        query: The main research query.
        subqueries: A list of sub-questions.
        documents_by_subq: Dictionary of scraped documents, organized by subquery.
        n_results: The target number of relevant documents per subquery.
        visited_urls: A set of URLs already visited to avoid duplicates.
        progress_callback: A function to update the UI's progress.
        max_new_url_attempts: The maximum number of *new, unvisited* URLs to attempt for each subquery
                              if initial documents are insufficient.

    Returns:
        A list of validated and summarized relevant documents.
    """
    current_step_idx = 4
    progress_callback(60, ALL_STEPS[current_step_idx], current_step_idx)
    validated_summaries = []

    for subq_idx, subq in enumerate(subqueries):
        progress_for_subq = 60 + int(20 * (subq_idx / len(subqueries)))
        progress_callback(progress_for_subq, f"{ALL_STEPS[current_step_idx]} : {subq}", current_step_idx)

        print(f"\n--- Traitement de la sous-question : {subq} ---")
        relevant_docs_for_subq = []

        initial_docs = documents_by_subq.get(subq, [])
        for doc in initial_docs:
            if len(relevant_docs_for_subq) >= n_results:
                break

            # Add initial document URLs to visited_urls to avoid re-processing later
            if doc.get("url"):
                visited_urls.add(doc.get("url"))

            if len(doc.get("paragraphs", "")) > 100:
                response_data = validate_and_summarize_document(query, subq, doc.get('paragraphs'))
                if response_data.get("is_relevant", False):
                    relevant_docs_for_subq.append({
                        "url": doc.get("url"),
                        "subquestion": doc.get("subquestion"),
                        "title": doc.get("title"),
                        "summary": response_data.get("summary")
                    })
                    print(f"✅ Document pertinent trouvé : {doc.get('url')}")
                else:
                    print(f"⚠️ Document de {doc.get('url')} jugé non pertinent.")
            else:
                if doc.get("paragraphs", "").strip():
                    relevant_docs_for_subq.append({
                        "url": doc.get("url"),
                        "subquestion": doc.get("subquestion"),
                        "title": doc.get("title"),
                        "summary": doc.get("paragraphs")  # Use raw content if too short for summarization
                    })
                    print(f"✅ Document court mais pertinent trouvé : {doc.get('url')}")
                else:
                    print(f"⚠️ Document de {doc.get('url')} est vide. Ignoré.")

        current_step_idx_retry = 6
        # Only proceed to fetch new URLs if we don't have enough documents
        if len(relevant_docs_for_subq) < n_results:
            print(f"♻️ Nombre de documents pertinents insuffisant pour '{subq}'. Recherche d'URLs de remplacement.")
            progress_callback(progress_for_subq,
                              f"{ALL_STEPS[current_step_idx_retry]} : {subq} (recherche de remplacement)",
                              current_step_idx_retry)

            # Fetch more search results than max_new_url_attempts, just in case many are already visited
            new_results_to_check = fetch_search_results_with_googlesearch(subq, max_new_url_attempts * 2) # Fetch more to have options
            new_urls_attempted_count = 0
            i = 0

            for new_title, new_url in new_results_to_check:
                # Stop if we have enough results or have attempted max_new_url_attempts *new* URLs
                if len(relevant_docs_for_subq) >= n_results or new_urls_attempted_count >= max_new_url_attempts or i >= (max_retry_document + 1):
                    break

                if new_url not in visited_urls:
                    print(f"✅ Nouvelle URL de remplacement potentielle : {new_url}")
                    visited_urls.add(new_url) # Mark as visited immediately upon attempt
                    new_urls_attempted_count += 1 # Increment only for truly new URLs we are processing

                    new_doc = scrape_worker_threaded({"url": new_url, "subquestion": subq})

                    if new_doc and len(new_doc.get("paragraphs", "")) > 100:
                        response_data = validate_and_summarize_document(query, subq, new_doc.get('paragraphs'))
                        if response_data.get("is_relevant", False):
                            relevant_docs_for_subq.append({
                                "url": new_doc.get("url"),
                                "subquestion": new_doc.get("subquestion"),
                                "title": new_doc.get("title"),
                                "summary": response_data.get("summary")
                            })
                            print(f"✅ Document de remplacement pertinent trouvé et ajouté.")
                        else:
                            print(f"⚠️ Document de {new_doc.get('url')} jugé non pertinent.")
                    elif new_doc and new_doc.get("paragraphs", "").strip():
                        relevant_docs_for_subq.append({
                            "url": new_doc.get("url"),
                            "subquestion": new_doc.get("subquestion"),
                            "title": new_doc.get("title"),
                            "summary": new_doc.get("paragraphs")
                        })
                        print(f"✅ Document de remplacement court mais pertinent trouvé : {new_doc.get('url')}")
                    else:
                        print(f"⚠️ Document de {new_doc.get('url')} est vide ou trop court. Ignoré.")
                else:
                    print(f"ℹ️ URL {new_url} déjà visitée ou en cours de traitement. Passons à la suivante.")

                i = i + 1

            if len(relevant_docs_for_subq) < n_results:
                print(f"❌ Impossible d'atteindre le nombre requis de documents pour '{subq}' après avoir essayé {new_urls_attempted_count} nouvelles URLs.")

        validated_summaries.extend(relevant_docs_for_subq)

    return validated_summaries


def _synthesize_final_answer(query: str, validated_summaries: list[dict], progress_callback) -> str:
    """
    Synthesizes the final answer from the validated document summaries.

    Args:
        query: The initial research query.
        validated_summaries: A list of relevant and summarized documents.
        progress_callback: A function to update the UI's progress.

    Returns:
        The final synthesized answer.
    """
    current_step_idx = 7
    progress_callback(85, ALL_STEPS[current_step_idx], current_step_idx)
    final_synthesis = None
    attempt = 0

    # Message par défaut si aucun document pertinent n'est trouvé
    if not validated_summaries:
        print("⚠️ Aucun document pertinent trouvé pour la synthèse. Génération d'une réponse par défaut.")
        return "Je n'ai pas pu trouver d'informations pertinentes sur le web pour répondre à votre question. Veuillez essayer une autre formulation ou un sujet différent."

    # Boucle de synthèse normale si des documents sont présents
    while final_synthesis is None and attempt < max_synth_retries:
        attempt += 1
        print(f"Tentative de synthèse n°{attempt}/{max_synth_retries}...")
        synth_msgs = [
            {"role": "system",
             "content": "Tu es un assistant de synthèse expert. Tu vas synthétiser les informations contenues dans les résumés pertinents fournis pour répondre à la question initiale. Utilise les URLs comme références. Et ne met pas de partie de reference."},
            {"role": "user",
             "content": json.dumps({"query": query, "data": validated_summaries}, ensure_ascii=False)}
        ]
        synth_content = request_mistral_model(synth_msgs)

        current_step_idx_validation = 8
        progress_callback(90, ALL_STEPS[current_step_idx_validation], current_step_idx_validation)
        print("\n✂️ Étape 4 : vérification de la cohérence de la synthèse...")
        validation_result = validate_final_synthesis(query, synth_content, validated_summaries)

        if validation_result.get("is_coherent", False):
            print("✅ La synthèse est cohérente et valide.")
            final_synthesis = synth_content
        else:
            print(f"⚠️ La synthèse est jugée incohérente. Raison : {validation_result.get('reason')}")
            if attempt < max_synth_retries:
                print("♻️ Nouvelle tentative de synthèse...")
            else:
                print("❌ Nombre maximal de tentatives de synthèse atteint. Renvoie de la derniere synthese.")
                final_synthesis = synth_content  # Return the last attempt even if incoherent
                break

    # Si après toutes les tentatives, la synthèse est toujours None (ce qui ne devrait pas arriver avec la ligne ci-dessus)
    if not final_synthesis:
        return "La synthèse n'a pas pu être générée de manière satisfaisante avec les documents trouvés."

    return final_synthesis


def perform_full_research(
        query: str,
        subqueries: list[str],
        n_results: int,
        progress_callback
) -> dict:
    """
    Performs the full research workflow: fetching, scraping, validation, and synthesis.
    Returns the final result dictionary.

    Args:
        query: The main research query.
        subqueries: A list of pre-generated sub-questions.
        n_results: The desired number of relevant results per subquery.
        progress_callback: A function to update the UI's progress.

    Returns:
        A dictionary containing the final synthesis, subquestions, and sources.
    """
    visited_urls = set()

    documents_by_subq = _fetch_and_scrape_urls(subqueries, n_results, visited_urls, progress_callback)

    validated_summaries = _process_documents(query, subqueries, documents_by_subq, n_results, visited_urls, progress_callback)

    final_synthesis = _synthesize_final_answer(query, validated_summaries, progress_callback)

    current_step_idx = 9
    progress_callback(100, ALL_STEPS[current_step_idx], current_step_idx)

    sources_by_subquery = []
    for sq in subqueries:
        urls = [doc["url"] for doc in validated_summaries if doc.get("subquestion") == sq]
        unique_urls = list(set(urls))
        sources_by_subquery.append({
            "subquestion": sq,
            "urls": unique_urls
        })
    return {
        "synthèse": final_synthesis,
        "sous_questions": subqueries,
        "sources": sources_by_subquery,
    }