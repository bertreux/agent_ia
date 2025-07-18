import os
import argparse
from agent.main_workflow import generate_subqueries_for_ui, perform_full_research, ALL_STEPS

def progress_callback(percentage: int, message: str, step_index: int):
    """
    Fonction de rappel simple pour afficher la progression en ligne de commande.
    """
    total_steps = len(ALL_STEPS)
    print(f"[{percentage}%] Étape {step_index + 1}/{total_steps}: {message}")

def main():
    parser = argparse.ArgumentParser(description="Effectue une recherche approfondie en utilisant l'IA.")
    parser.add_argument("query", type=str, help="La question principale de la recherche.")
    parser.add_argument("-k", "--subqueries", type=int, default=3,
                        help="Nombre de sous-questions à générer (par défaut: 3).")
    parser.add_argument("-n", "--results_per_subquery", type=int, default=2,
                        help="Nombre de résultats pertinents à collecter par sous-question (par défaut: 2).")
    args = parser.parse_args()

    if not os.environ.get("MISTRAL_API_KEY"):
        print("Erreur : La variable d'environnement MISTRAL_API_KEY n'est pas définie.")
        print("Veuillez la définir avant de lancer le script (e.g., export MISTRAL_API_KEY='votre_clé').")
        return

    print(f"🚀 Démarrage de la recherche pour : '{args.query}'")
    print(f"⚙️ Paramètres : {args.subqueries} sous-questions, {args.results_per_subquery} résultats par sous-question.")

    try:
        print("\n--- Génération des sous-questions ---")
        subqs = generate_subqueries_for_ui(args.query, args.subqueries, progress_callback)

        if not subqs:
            print("❌ Aucune sous-question générée. Arrêt de la recherche.")
            return

        print("\n--- Lancement de la recherche complète ---")
        final_output = perform_full_research(
            args.query,
            subqs,
            args.results_per_subquery,
            progress_callback
        )

        print("\n--- 🎉 Recherche Terminée 🎉 ---")
        print("\n## Synthèse Finale")
        print(final_output['synthèse'])

        print("\n## Sous-questions explorées")
        for i, sq in enumerate(final_output['sous_questions']):
            print(f"- {i+1}. {sq}")

        print("\n## Sources utilisées")
        for source_group in final_output['sources']:
            print(f"\n### Sous-question : {source_group['subquestion']}")
            if source_group['urls']:
                for url in source_group['urls']:
                    print(f"- {url}")
            else:
                print("- Aucune URL pertinente trouvée pour cette sous-question.")

    except Exception as e:
        print(f"\n❌ Une erreur inattendue est survenue : {e}")

if __name__ == "__main__":
    main()