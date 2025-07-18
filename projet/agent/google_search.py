from googlesearch import search
import time

def fetch_search_results_with_googlesearch(query, n=5, retries=3):
    results = []
    for attempt in range(retries):
        try:
            for url in search(query, num_results=n):
                results.append(("", url))
            return results
        except Exception as e:
            print(f"Erreur durant la recherche avec googlesearch (tentative {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return []
    return []