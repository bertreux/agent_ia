import os
import streamlit as st
import hashlib
import json
from datetime import datetime
from deep_research import deep_research
from streamlit.components.v1 import html

HISTORY_DIR = "historique"
os.makedirs(HISTORY_DIR, exist_ok=True)

def hash_query(query, k, n, timestamp):
    return hashlib.md5(f"{query}-{k}-{n}-{timestamp}".encode()).hexdigest()

def save_new_history(full_query, k, n, result, display_query):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    key = hash_query(full_query, k, n, timestamp)
    filename = f"{timestamp}_{key[:6]}.json"
    filepath = os.path.join(HISTORY_DIR, filename)
    history_entry = {
        "full_query": full_query,
        "display_query": display_query,
        "k": k,
        "n": n,
        "result": result["synthèse"],
        "subqueries": result["sous_questions"],
        "sources_by_subquery": result["sources"],
        "timestamp": timestamp
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"initial_query": display_query, "history": [history_entry]}, f, ensure_ascii=False, indent=2)
    return filename

def update_history(filename, full_query, k, n, result, display_query):
    filepath = os.path.join(HISTORY_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        st.error("Fichier d'historique non trouvé pour la mise à jour.")
        return None

    if "history" not in data:
        data = {"history": [data]}

    history_entry = {
        "full_query": full_query,
        "display_query": display_query,
        "k": k,
        "n": n,
        "result": result["synthèse"],
        "subqueries": result["sous_questions"],
        "sources_by_subquery": result["sources"],
        "timestamp": datetime.now().strftime("%Y%m%d-%H%M%S")
    }
    data["history"].append(history_entry)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filename

def load_all_histories():
    entries = []
    for filename in sorted(os.listdir(HISTORY_DIR), reverse=True):
        if filename.endswith(".json"):
            path = os.path.join(HISTORY_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)

                    if "initial_query" in data:
                        display_name = data["initial_query"]
                    elif "history" in data and len(data["history"]) > 0:
                        display_name = data["history"][0].get('display_query', data["history"][0].get('query'))
                    elif 'query' in data:
                        display_name = data['query']
                    else:
                        continue

                    entries.append({
                        "filename": filename,
                        "display_name": display_name,
                        "timestamp": data.get("history", [{}])[-1].get("timestamp", data.get("timestamp"))
                    })
                except Exception:
                    continue
    return entries

def load_full_history_by_filename(filename):
    filepath = os.path.join(HISTORY_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if "history" in data:
                    return data["history"]
                return [data]
            except Exception:
                return []
    return []

def delete_history_file(filename):
    try:
        os.remove(os.path.join(HISTORY_DIR, filename))
        st.success(f"🗑️ Historique supprimé : {filename}")
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"❌ Erreur lors de la suppression : {e}")

def run_deep_research(query, k, n, display_query=None, history_filename=None):
    if "MISTRAL_API_KEY" not in os.environ:
        st.error("❌ Veuillez définir la variable d'environnement MISTRAL_API_KEY.")
        return
    elif not query.strip():
        st.warning("Veuillez entrer une question.")
        return

    if display_query is None:
        display_query = query

    progress_text = st.empty()
    progress_bar = st.progress(0)

    def update_progress(percentage, status_message):
        progress_bar.progress(percentage)
        progress_text.info(f"💡 {status_message}")

    try:
        result = deep_research(query, n, k, progress_callback=update_progress)

        if history_filename:
            filename = update_history(history_filename, query, k, n, result, display_query=display_query)
        else:
            filename = save_new_history(query, k, n, result, display_query=display_query)

        st.query_params["entry"] = filename
        st.rerun()
    except Exception as e:
        st.error(f"❌ Une erreur est survenue lors de la recherche : {e}")
    finally:
        progress_bar.empty()
        progress_text.empty()

st.set_page_config(page_title="Recherche Profonde", page_icon="🧠", layout="wide")

st.sidebar.title("🧠 Recherche Profonde")
histories = load_all_histories()
menu_choices = ["➕ Nouvelle requête"] + [
    f"{h.get('display_name', 'Requête sans nom')} ({h.get('timestamp', 'Inconnu')})" for h in histories
]

selected_filename_from_url = st.query_params.get("entry")
selected_index = 0
if selected_filename_from_url:
    try:
        index = next((i for i, h in enumerate(histories) if h['filename'] == selected_filename_from_url), None)
        if index is not None:
            selected_index = index + 1
    except (StopIteration, ValueError):
        st.query_params.clear()
        st.rerun()

menu_choice = st.sidebar.radio("Menu", menu_choices, index=selected_index)

current_selected_filename = None
if menu_choice == "➕ Nouvelle requête":
    if "entry" in st.query_params:
        del st.query_params["entry"]
        st.rerun()
else:
    selected_entry = histories[menu_choices.index(menu_choice) - 1]
    current_selected_filename = selected_entry["filename"]
    if st.query_params.get("entry") != current_selected_filename:
        st.query_params["entry"] = current_selected_filename
        st.rerun()

if menu_choice == "➕ Nouvelle requête":
    st.title("🔎 Nouvelle recherche profonde")
    query = st.text_input(
        "Pose ta question ici :",
        value="",
        placeholder="Ex : Pourquoi la tour Eiffel a-t-elle été construite ?"
    )
    col1, col2 = st.columns(2)
    with col1:
        k = st.number_input("Nombre de sous-questions à générer", min_value=1, max_value=10, value=3)
    with col2:
        n = st.number_input("Nombre de sites à récupérer par sous-question", min_value=1, max_value=10, value=3)

    if st.button("Lancer la recherche"):
        run_deep_research(query, k, n)

else:
    selected_filename = current_selected_filename
    full_history = load_full_history_by_filename(selected_filename)

    if not full_history:
        st.error("Historique non trouvé ou corrompu. Il a peut-être été supprimé.")
        st.query_params.clear()
        st.stop()

    initial_query = full_history[0].get('display_query', 'Requête sans titre')
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
                st.markdown(entry["result"])

        with col2:
            with st.container(border=True):
                query_to_display = entry.get('display_query', entry.get('full_query', entry.get('query', '')))
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
                        for url in group["urls"]:
                            st.markdown(f"- [{url}]({url})")

        st.markdown("---")

    st.markdown("### 🔍 Affiner ou poursuivre cette recherche")

    with st.form(key="refine_query_form"):
        new_query = st.text_input("Nouvelle demande :", placeholder="Ex : mais aussi le meilleur 4 étoiles.")

        col1, col2 = st.columns(2)
        with col1:
            k = st.number_input("Nombre de sous-questions à générer", min_value=1, max_value=10,
                                value=full_history[-1]["k"], key="k_refine")
        with col2:
            n = st.number_input("Nombre de sites à récupérer par sous-question", min_value=1, max_value=10,
                                value=full_history[-1]["n"], key="n_refine")

        submit_button = st.form_submit_button(label="Lancer la nouvelle recherche")

        if submit_button and new_query.strip():
            combined_context_list = []
            for entry in full_history:
                full_query_to_add = entry.get('full_query', entry.get('query'))
                combined_context_list.append(f"Requête : {full_query_to_add}\nSynthèse : {entry['result']}")

            context_string = "\n\n".join(combined_context_list)

            combined_query = f"Contexte de recherche :\n{context_string}\n\nNouvelle demande : {new_query}"
            run_deep_research(combined_query, k, n, display_query=new_query, history_filename=selected_filename)
        elif submit_button and not new_query.strip():
            st.warning("Veuillez entrer une nouvelle demande pour continuer la recherche.")

    st.markdown("---")

    if st.button("🗑️ Supprimer cet historique"):
        delete_history_file(selected_filename)

    st.markdown("\n")

    st.markdown('<div id="scroll-to-here"></div>', unsafe_allow_html=True)
    js = """
    <script>
        var element = window.parent.document.getElementById('scroll-to-here');
        if (element) {
            element.scrollIntoView({behavior: "smooth", block: "end"});
        }
    </script>
    """
    html(js, height=0)