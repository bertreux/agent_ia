import os
import streamlit as st
import hashlib
import json
from datetime import datetime
from deep_research import generate_subqueries_for_ui, perform_full_research, ALL_STEPS
import pyperclip
from streamlit.components.v1 import html

# --- Constants ---
HISTORY_DIR = "historique"
os.makedirs(HISTORY_DIR, exist_ok=True)

# --- Utility Functions ---
def hash_query(query, k, n, timestamp):
    """Generates an MD5 hash for a given query and parameters."""
    return hashlib.md5(f"{query}-{k}-{n}-{timestamp}".encode()).hexdigest()


def save_history_entry(full_query, k, n, result, display_query, filename=None):
    """
    Saves a new history entry or updates an existing one.
    If filename is provided, it updates the file. Otherwise, it creates a new file.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    history_entry = {
        "full_query": full_query,
        "display_query": display_query,
        "k": k,
        "n": n,
        "result": result["synthèse"],
        "subqueries": result["sous_questions"],
        "sources_by_subquery": result["sources"],
        "timestamp": timestamp,
    }

    if filename:
        filepath = os.path.join(HISTORY_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            st.session_state.error_message = "Fichier d'historique non trouvé pour la mise à jour."
            return None

        if "history" not in data:
            data = {"history": [data]}  # Convert old format to new list format
        data["history"].append(history_entry)

    else:
        key = hash_query(full_query, k, n, timestamp)
        filename = f"{timestamp}_{key[:6]}.json"
        filepath = os.path.join(HISTORY_DIR, filename)
        data = {"initial_query": display_query, "history": [history_entry]}

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename


def load_all_histories():
    """Loads metadata for all saved history files."""
    entries = []
    for filename in sorted(os.listdir(HISTORY_DIR), reverse=True):
        if filename.endswith(".json"):
            path = os.path.join(HISTORY_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    display_name = data.get("initial_query")
                    if not display_name and "history" in data and len(data["history"]) > 0:
                        display_name = data["history"][0].get('display_query', data["history"][0].get('full_query'))

                    if display_name:
                        entries.append({
                            "filename": filename,
                            "display_name": display_name,
                            "timestamp": data.get("history", [{}])[-1].get("timestamp", "")
                        })
            except Exception:
                # Skip corrupted or unreadable files
                continue
    return entries


def load_full_history_by_filename(filename):
    """Loads the complete history for a given filename."""
    if not filename: # Add this check!
        st.session_state.error_message = "Nom de fichier d'historique manquant. Impossible de charger."
        return []

    filepath = os.path.join(HISTORY_DIR, filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "history" in data:
                    return data["history"]
                return [data]  # Handle older single-entry files
        except Exception:
            st.session_state.error_message = f"Erreur de lecture du fichier d'historique : {filename}. Il est peut-être corrompu."
            return []
    st.session_state.error_message = f"Fichier d'historique non trouvé : {filename}. Il a peut-être été supprimé."
    return []


def delete_history_file(filename):
    """Deletes a history file."""
    try:
        os.remove(os.path.join(HISTORY_DIR, filename))
        st.success(f"🗑️ Historique supprimé : {filename}")
        # Reset session state for a clean start after deletion
        st.session_state.current_step = 0
        st.session_state.subqueries_editable = []
        st.query_params.clear()
        st.session_state.error_message = None # Clear any error
        st.rerun()
    except Exception as e:
        st.session_state.error_message = f"❌ Erreur lors de la suppression : {e}"
        st.rerun()


def delete_single_history_entry(filename, index_to_delete):
    """Deletes a specific entry from a history file."""
    filepath = os.path.join(HISTORY_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        st.session_state.error_message = "Fichier d'historique non trouvé pour la suppression."
        st.rerun()
        return

    if "history" not in data:
        data = {"history": [data]}

    if not (0 <= index_to_delete < len(data["history"])):
        st.session_state.error_message = "Index de synthèse invalide pour la suppression."
        st.rerun()
        return

    del data["history"][index_to_delete]

    if not data["history"]:  # If no entries left, delete the file
        delete_history_file(filename)
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.success("🗑️ Synthèse supprimée !")
        st.session_state.error_message = None # Clear any error
        st.query_params["entry"] = filename
        st.rerun()

def regenerate_and_replace_history(filename, index_to_replace, original_query, original_k, original_n,
                                   original_display_query, original_subqueries):
    filepath = os.path.join(HISTORY_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        st.session_state.error_message = "Fichier d'historique non trouvé pour la régénération."
        st.session_state.current_step = 3 # Stay on history page
        st.rerun()
        return

    if "history" not in data:
        data = {"history": [data]}

    if not (0 <= index_to_replace < len(data["history"])):
        st.session_state.error_message = "Index de synthèse invalide pour la régénération."
        st.session_state.current_step = 3 # Stay on history page
        st.rerun()
        return

    # --- Progress display for regeneration ---
    progress_container = st.container()
    progress_bar = progress_container.progress(0)
    progress_status_text = progress_container.empty()
    steps_display_container = progress_container.empty()

    # Pass ALL_STEPS to the callback as it's no longer an instance variable
    def update_progress_for_regeneration(percentage, status_message, current_step_idx):
        progress_bar.progress(percentage / 100)
        progress_status_text.info(f"💡 **Statut actuel :** {status_message}")

        steps_markdown = ""
        for i, step_name in enumerate(ALL_STEPS): # Use the imported ALL_STEPS
            if i < current_step_idx:
                steps_markdown += f"- ✅ {step_name}\n"
            elif i == current_step_idx:
                steps_markdown += f"- 👉 **{step_name}**\n"
            else:
                steps_markdown += f"- ⏳ {step_name}\n"
        steps_display_container.markdown(steps_markdown)

    try:
        # Call the core research function with the original subqueries
        result = perform_full_research(
            query=original_query,
            subqueries=original_subqueries, # Use the stored subqueries directly
            n_results=original_n,
            progress_callback=update_progress_for_regeneration
        )

        if result is None or not result["synthèse"]: # Check if synthesis is empty
            st.session_state.error_message = "❌ La régénération n'a pas pu aboutir à un résultat complet ou pertinent. Veuillez réessayer."
            st.session_state.current_step = 3 # Stay on history page
            st.rerun()
            return

        data["history"][index_to_replace] = {
            "full_query": original_query,
            "display_query": original_display_query,
            "k": len(original_subqueries), # K is now based on actual subqueries
            "n": original_n,
            "result": result["synthèse"],
            "subqueries": result["sous_questions"],
            "sources_by_subquery": result["sources"],
            "timestamp": datetime.now().strftime("%Y%m%d-%H%M%S")
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        st.success("✅ Synthèse régénérée avec succès !")
        st.session_state.error_message = None # Clear any error
        st.query_params["entry"] = filename
        st.session_state.current_step = 3 # Go back to result display step
        st.rerun()

    except Exception as e:
        st.session_state.error_message = f"❌ Une erreur est survenue lors de la régénération : {e}. Veuillez réessayer."
        st.session_state.current_step = 3 # Stay on history page
        st.rerun()
    finally:
        progress_container.empty()

def update_progress_ui(progress_bar, status_text_holder, steps_display_holder, percentage, status_message,
                       current_step_idx):
    """Updates the progress bar and status text in the UI."""
    progress_bar.progress(percentage / 100)
    status_text_holder.info(f"💡 **Statut actuel :** {status_message}")

    steps_markdown = ""
    for i, step_name in enumerate(ALL_STEPS):
        if i < current_step_idx:
            steps_markdown += f"- ✅ {step_name}\n"
        elif i == current_step_idx:
            steps_markdown += f"- 👉 **{step_name}**\n"
        else:
            steps_markdown += f"- ⏳ {step_name}\n"
    steps_display_holder.markdown(steps_markdown)


# --- Streamlit UI Components and Logic ---
def setup_page_config():
    """Sets up the Streamlit page configuration."""
    st.set_page_config(page_title="Recherche Profonde", page_icon="🧠", layout="wide")


def initialize_session_state():
    """Initializes necessary session state variables."""
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 0
    if 'subqueries_editable' not in st.session_state:
        st.session_state.subqueries_editable = []
    # Initialize with default values, not linked directly to a widget yet
    if 'main_query_input' not in st.session_state:
        st.session_state.main_query_input = ""
    if 'k_pick_config' not in st.session_state:
        st.session_state.k_pick_config = 3
    if 'n_results_config' not in st.session_state:
        st.session_state.n_results_config = 3
    if 'display_query_for_history' not in st.session_state:
        st.session_state.display_query_for_history = ""
    if 'current_history_filename' not in st.session_state:
        st.session_state.current_history_filename = None
    if 'active_query_for_research' not in st.session_state:
        st.session_state.active_query_for_research = ""
    if 'refinement_triggered' not in st.session_state:
        st.session_state.refinement_triggered = False
    if 'error_message' not in st.session_state: # New: for persistent error messages
        st.session_state.error_message = None


def render_sidebar():
    """Renders the sidebar with history navigation."""
    st.sidebar.title("🧠 Recherche Profonde")
    histories = load_all_histories()
    menu_choices = ["➕ Nouvelle requête"] + [
        f"{h.get('display_name', 'Requête sans nom')} ({h.get('timestamp', 'Inconnu')})" for h in histories
    ]

    selected_filename_from_url = st.query_params.get("entry")
    selected_index = 0
    current_selected_filename = None # Initialize here to ensure it's always defined

    if selected_filename_from_url:
        try:
            index = next((i for i, h in enumerate(histories) if h['filename'] == selected_filename_from_url), None)
            if index is not None:
                selected_index = index + 1
                current_selected_filename = selected_filename_from_url # Set filename if found in URL
                st.session_state.current_step = 3
                st.session_state.current_history_filename = current_selected_filename
                st.session_state.error_message = None # Clear error on history load
        except (StopIteration, ValueError):
            st.query_params.clear()
            st.session_state.current_step = 0
            st.session_state.error_message = None # Clear error
            st.rerun()

    # The radio button will return the string, we need to map it back to filename
    menu_choice = st.sidebar.radio("Menu", menu_choices, index=selected_index, key="sidebar_menu")

    if menu_choice == "➕ Nouvelle requête":
        if "entry" in st.query_params:
            del st.query_params["entry"]
            st.session_state.current_step = 0
            st.session_state.current_history_filename = None
            st.session_state.error_message = None # Clear error on new query
            st.rerun()
        # If it's a new query, current_selected_filename should be None
        current_selected_filename = None
    else:
        # Find the selected entry's filename from the histories list
        # This covers both initial load from URL and subsequent sidebar clicks
        try:
            selected_entry = next(h for h in histories if f"{h.get('display_name', 'Requête sans nom')} ({h.get('timestamp', 'Inconnu')})" == menu_choice)
            current_selected_filename = selected_entry["filename"]
            if st.query_params.get("entry") != current_selected_filename:
                st.query_params["entry"] = current_selected_filename
                st.session_state.current_step = 3
                st.session_state.current_history_filename = current_selected_filename
                st.session_state.error_message = None # Clear error on history load
                st.rerun()
        except StopIteration:
            # This case should ideally not happen if histories is correctly populated
            # and menu_choice is valid, but good for robustness.
            st.session_state.error_message = "Impossible de trouver l'entrée d'historique sélectionnée."
            st.session_state.current_step = 0 # Go back to new query if something's off
            st.rerun()

    return current_selected_filename


def step_0_new_query():
    """Renders the UI for starting a new query."""
    st.title("🔎 Nouvelle recherche profonde")
    st.write("Entrez la question ou le sujet que vous souhaitez explorer en profondeur.")

    # Get the direct value from the widget
    main_query_input_value = st.text_area(
        "Votre question :",
        value=st.session_state.main_query_input, # Use initial session state value for display
        key="main_query_input_widget",
        placeholder="Ex : Pourquoi la tour Eiffel a-t-elle été construite ?"
    )

    col1, col2 = st.columns(2)
    with col1:
        k_pick_config_value = st.number_input(
            "Nombre de sous-questions à générer",
            min_value=1, max_value=10, value=st.session_state.k_pick_config, # Use initial session state value
            key="k_pick_config_widget"
        )
    with col2:
        n_results_config_value = st.number_input(
            "Nombre de sites à récupérer par sous-question",
            min_value=1, max_value=10, value=st.session_state.n_results_config, # Use initial session state value
            key="n_results_config_widget"
        )

    if st.button("Lancer la recherche initiale"):
        if main_query_input_value: # Use the value directly from the widget
            # Update session state with the current widget values
            st.session_state.main_query_input = main_query_input_value
            st.session_state.k_pick_config = k_pick_config_value
            st.session_state.n_results_config = n_results_config_value

            st.session_state.active_query_for_research = st.session_state.main_query_input
            st.session_state.display_query_for_history = st.session_state.main_query_input
            st.session_state.current_step = 1
            st.session_state.subqueries_editable = []
            st.session_state.refinement_triggered = False
            st.session_state.error_message = None # Clear error on new search
            st.rerun()
        else:
            st.warning("Veuillez entrer une question pour démarrer la recherche.")


def step_1_generate_subqueries():
    """Renders the UI for generating and reviewing sub-queries."""
    st.subheader("Étape 1: Génération et révision des sous-questions")
    st.write(
        "L'IA a généré les sous-questions suivantes pour approfondir votre recherche. Vous pouvez les modifier si vous le souhaitez.")

    progress_container = st.container()
    progress_bar = progress_container.progress(0)
    progress_status_text = progress_container.empty()
    steps_display_container = progress_container.empty()

    def progress_callback_wrapper(percentage, status_message, step_index):
        update_progress_ui(progress_bar, progress_status_text, steps_display_container,
                           percentage, status_message, step_index)

    if not st.session_state.subqueries_editable:
        try:
            with st.spinner("Génération des sous-questions par l'IA..."):
                generated_subqueries = generate_subqueries_for_ui(
                    st.session_state.active_query_for_research,
                    st.session_state.k_pick_config,
                    progress_callback_wrapper
                )
                st.session_state.subqueries_editable = generated_subqueries[:]
                progress_container.empty()  # Clear progress indicators after completion
                st.session_state.error_message = None # Clear error on successful generation
        except Exception as e:
            st.session_state.error_message = f"❌ Erreur lors de la génération des sous-questions : {e}. Veuillez réessayer."
            # If subquery generation fails, decide where to send the user
            # For refinement, we want to go back to the history view
            if st.session_state.refinement_triggered:
                st.session_state.current_step = 3
                st.session_state.refinement_triggered = False # Reset flag
                st.rerun()
            else: # For initial search, go back to step 0
                st.session_state.current_step = 0
                st.rerun()


    if st.session_state.subqueries_editable:
        edited_subqueries = []
        for i, subq in enumerate(st.session_state.subqueries_editable):
            edited_subqueries.append(st.text_input(f"Sous-question {i + 1}:", value=subq, key=f"subq_input_{i}"))

        if st.button("Valider les sous-questions et continuer"):
            st.session_state.subqueries_editable = edited_subqueries
            st.session_state.current_step = 2
            st.session_state.error_message = None # Clear error on continuing
            st.rerun()
    else:
        st.warning("Impossible de générer des sous-questions. Veuillez réessayer.")
        if st.session_state.refinement_triggered:
            if st.button("Revenir à l'historique"):
                st.session_state.current_step = 3
                st.session_state.refinement_triggered = False # Reset flag
                st.session_state.error_message = None # Clear error
                st.rerun()
        else:
            if st.button("Revenir à la question initiale"):
                st.session_state.current_step = 0
                st.session_state.error_message = None # Clear error
                st.rerun()


def step_2_perform_research():
    """Renders the UI for ongoing research and displays progress."""
    st.subheader("Étape 2: Recherche en cours...")
    st.write("Veuillez patienter pendant que l'IA collecte et synthétise les informations.")

    progress_container = st.container()
    progress_bar = progress_container.progress(0)
    progress_status_text = progress_container.empty()
    steps_display_container = progress_container.empty()

    def progress_callback_wrapper(percentage, status_message, current_step_idx):
        update_progress_ui(progress_bar, progress_status_text, steps_display_container,
                           percentage, status_message, current_step_idx)

    try:
        final_result = perform_full_research(
            query=st.session_state.active_query_for_research,
            subqueries=st.session_state.subqueries_editable,
            n_results=st.session_state.n_results_config,
            progress_callback=progress_callback_wrapper
        )

        if final_result and final_result["synthèse"]: # Check if synthesis is not empty
            filename = save_history_entry(
                st.session_state.active_query_for_research,
                len(st.session_state.subqueries_editable),
                st.session_state.n_results_config,
                final_result,
                st.session_state.display_query_for_history,
                filename=st.session_state.current_history_filename
            )
            st.query_params["entry"] = filename
            st.session_state.current_history_filename = filename
            st.session_state.current_step = 3
            st.session_state.refinement_triggered = False # Reset flag after successful research
            st.session_state.error_message = None # Clear any error on success
            st.rerun()
        else:
            st.session_state.error_message = "❌ La recherche n'a pas pu aboutir à un résultat complet ou pertinent. Cela peut arriver si aucun document pertinent n'a été trouvé."
            # Decide where to go if no result is found
            if st.session_state.refinement_triggered:
                st.session_state.current_step = 3 # Back to history for refinement attempts
            else:
                st.session_state.current_step = 0 # Back to initial query for new search
            st.session_state.refinement_triggered = False # Reset flag on failure
            st.rerun()
    except Exception as e:
        st.session_state.error_message = f"❌ Une erreur est survenue lors de la recherche : {e}. Veuillez réessayer."
        # Decide where to go on exception
        if st.session_state.refinement_triggered:
            st.session_state.current_step = 3 # Back to history for refinement attempts
        else:
            st.session_state.current_step = 0 # Back to initial query for new search
        st.session_state.refinement_triggered = False # Reset flag on failure
        st.rerun()
    finally:
        progress_container.empty()


def step_3_display_history(selected_filename):
    # This check is crucial now
    if not selected_filename:
        st.session_state.error_message = "Aucun historique n'est sélectionné ou l'historique a été supprimé. Veuillez choisir une autre entrée ou lancer une nouvelle requête."
        st.session_state.current_step = 0
        st.session_state.current_history_filename = None
        st.rerun()
        return # Important to return here to prevent further execution with None

    full_history = load_full_history_by_filename(selected_filename)

    if not full_history:
        # The error message is already set by load_full_history_by_filename
        st.query_params.clear()
        st.session_state.current_step = 0
        st.session_state.current_history_filename = None
        st.rerun()
        return # Important to return here

    initial_query = full_history[0].get('display_query', full_history[0].get('full_query', 'Requête sans titre'))
    st.title(f"📄 Historique de la conversation : {initial_query}")
    st.markdown("---")

    for i, entry in enumerate(full_history):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                """
                <style>
                .response-container {
                    background-color: #f0f2f6;
                    border-radius: 5px;
                    padding: 1rem;
                    border: 1px solid #e0e2e6;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            with st.container(border=True):
                st.markdown(entry['result'])

                col_buttons = st.columns([1, 1, 1])

                with col_buttons[0]:
                    if st.button("📋 Copier", key=f"copy_button_{i}"):
                        try:
                            pyperclip.copy(entry['result'])
                            st.toast("Synthèse copiée !")
                        except Exception as e:
                            st.toast(
                                f"Erreur de copie: {e}. Note: Ceci ne copie PAS sur le presse-papiers de votre navigateur.")

                with col_buttons[1]:
                    if st.button("♻️ Régénérer", key=f"regenerate_button_{i}"):
                        st.info("Régénération en cours...")
                        # Get the original parameters for regeneration
                        original_full_query = entry['full_query']
                        original_k = entry['k']
                        original_n = entry['n']
                        original_display_query = entry.get('display_query', original_full_query)
                        original_subqueries = entry['subqueries']

                        regenerate_and_replace_history(
                            selected_filename,
                            i,
                            original_full_query,
                            original_k,
                            original_n,
                            original_display_query,
                            original_subqueries
                        )

                with col_buttons[2]:
                    if st.button("🗑️ Supprimer", key=f"delete_single_button_{i}"):
                        delete_single_history_entry(selected_filename, i)

        with col2:
            with st.container(border=True):
                query_to_display = entry.get('display_query', entry.get('full_query', ''))
                st.markdown(f"### {query_to_display}")
                st.markdown("---")
                st.markdown(f"**🕒 Date :** {entry['timestamp']}")
                st.markdown(f"**📌 Paramètres :** {entry['k']} sous-questions, {entry['n']} sites")
                if "subqueries" in entry:
                    st.markdown("---")
                    st.markdown("### ❓ Sous-questions générées")
                    for j, sq in enumerate(entry["subqueries"], 1):
                        st.markdown(f"- **{j}.** {sq}")
                if "sources_by_subquery" in entry:
                    st.markdown("---")
                    st.markdown("### 🌐 Sites scrappés")
                    for group in entry["sources_by_subquery"]:
                        st.markdown(f"**Sous-question :** {group['subquestion']}")
                        if group["urls"]:
                            for url in group["urls"]:
                                st.markdown(f"- [{url}]({url})")
                        else:
                            st.markdown("  *Aucun site pertinent trouvé pour cette sous-question.*")
        st.markdown("---")

    st.markdown("### 🔍 Affiner ou poursuivre cette recherche")

    # Always display the refinement form
    with st.form(key="refine_query_form"):
        new_query_for_refinement = st.text_input("Nouvelle demande :",
                                                 placeholder="Ex : mais aussi le meilleur 4 étoiles.")

        col1, col2 = st.columns(2)
        with col1:
            k_refine = st.number_input("Nombre de sous-questions à générer", min_value=1, max_value=10,
                                       value=full_history[-1]["k"], key="k_refine")
        with col2:
            n_refine = st.number_input("Nombre de sites à récupérer par sous-question", min_value=1, max_value=10,
                                       value=full_history[-1]["n"], key="n_refine")

        # This button initiates the *process* of refinement, which includes subquery generation
        submit_button_refine = st.form_submit_button(label="Lancer la recherche")

        if submit_button_refine:
            if new_query_for_refinement.strip():
                combined_context_list = []
                for entry in full_history:
                    full_query_to_add = entry.get('full_query')
                    combined_context_list.append(f"Requête : {full_query_to_add}\nSynthèse : {entry['result']}")

                context_string = "\n\n".join(combined_context_list)
                combined_query_for_workflow = f"Contexte de recherche :\n{context_string}\n\nNouvelle demande : {new_query_for_refinement}"

                st.session_state.active_query_for_research = combined_query_for_workflow
                st.session_state.display_query_for_history = new_query_for_refinement
                st.session_state.k_pick_config = k_refine
                st.session_state.n_results_config = n_refine
                st.session_state.current_history_filename = selected_filename
                st.session_state.subqueries_editable = []
                st.session_state.refinement_triggered = True
                st.session_state.error_message = None # Clear error on new refinement

                # Crucial: Clear the 'entry' param before moving to subquery generation
                if "entry" in st.query_params:
                    del st.query_params["entry"]
                st.session_state.current_step = 1 # Go to step 1 to generate and review subqueries
                st.rerun()

            else:
                st.warning("Veuillez entrer une nouvelle demande pour affiner la recherche.")

    # This block will now be shown after 'Préparer l'affinement' is clicked and reruns to step 1
    # It will not be part of the initial form submission anymore.
    if st.session_state.refinement_triggered and st.session_state.current_step == 1:
        st.markdown("---")
        st.subheader("💡 Génération des sous-questions pour l'affinement...")

        temp_progress_container = st.container()
        temp_progress_bar = temp_progress_container.progress(0)
        temp_progress_status_text = temp_progress_container.empty()
        temp_steps_display_container = temp_progress_container.empty()

        def temp_update_progress_for_subquery_gen(percentage, status_message, step_index):
            update_progress_ui(temp_progress_bar, temp_progress_status_text,
                               temp_steps_display_container, percentage, status_message, step_index)

        if not st.session_state.subqueries_editable: # Only generate if not already generated
            try:
                with st.spinner("Génération des sous-questions par l'IA pour l'affinement..."):
                    generated_subqueries = generate_subqueries_for_ui(
                        st.session_state.active_query_for_research,
                        st.session_state.k_pick_config,
                        temp_update_progress_for_subquery_gen
                    )
                    st.session_state.subqueries_editable = generated_subqueries[:]
                temp_progress_container.empty()
                st.success("✅ Sous-questions générées !")
                st.session_state.error_message = None # Clear error on successful generation

            except Exception as e:
                st.session_state.error_message = f"❌ Erreur lors de la génération des sous-questions pour l'affinement : {e}"
                st.session_state.current_step = 3
                st.session_state.refinement_triggered = False
                temp_progress_container.empty()
                st.rerun()

        if st.session_state.subqueries_editable:
            st.markdown("---")
            st.subheader("📝 Révision des sous-questions générées pour l'affinement")
            st.write("Veuillez réviser et valider les sous-questions ci-dessous :")
            edited_refinement_subqueries = []
            for idx, subq in enumerate(st.session_state.subqueries_editable):
                edited_refinement_subqueries.append(st.text_input(f"Sous-question {idx+1}:", value=subq, key=f"refine_subq_input_{idx}"))

            if st.button("Valider et Lancer la recherche d'affinement", key="launch_refinement_research"):
                st.session_state.subqueries_editable = edited_refinement_subqueries
                st.session_state.current_step = 2
                st.session_state.error_message = None # Clear error on continuing
                st.rerun()
        else:
            st.warning("Aucune sous-question n'a pu être générée pour l'affinement. Veuillez modifier votre demande.")
            st.session_state.current_step = 3
            st.session_state.refinement_triggered = False

    st.markdown("---")

    col_bottom_buttons = st.columns([1, 4])
    with col_bottom_buttons[0]:
        if st.button("🗑️ Supprimer cet historique"):
            delete_history_file(selected_filename)

    st.markdown("\n")
    st.markdown('<div id="scroll-to-here"></div>', unsafe_allow_html=True)
    js_scroll = """
    <script>
        var element = window.parent.document.getElementById('scroll-to-here');
        if (element) {
            element.scrollIntoView({behavior: "smooth", block: "end"});
        }
    </script>
    """
    html(js_scroll, height=0)

# --- Main Application Flow ---
def main():
    setup_page_config()
    initialize_session_state()

    # Display persistent error message if it exists
    if st.session_state.error_message:
        st.error(st.session_state.error_message)

    current_selected_filename = render_sidebar()

    # Crucial check: Ensure current_selected_filename is not None when entering step 3
    if st.session_state.current_step == 3 and current_selected_filename is None:
        st.session_state.error_message = "Impossible d'afficher l'historique car aucun fichier n'a été sélectionné ou trouvé."
        st.session_state.current_step = 0 # Redirect to new query page
        st.rerun()
        return # Stop execution to prevent the TypeError


    if st.session_state.current_step == 0:
        step_0_new_query()
    elif st.session_state.current_step == 1:
        step_1_generate_subqueries()
    elif st.session_state.current_step == 2:
        step_2_perform_research()
    elif st.session_state.current_step == 3:
        step_3_display_history(current_selected_filename)


if __name__ == "__main__":
    main()