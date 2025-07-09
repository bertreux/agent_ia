import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# --- STYLE & CONFIGURATION ---
st.set_page_config(page_title="Dashboard IE1 – Techniques & Stats", layout="wide")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data(filename: str) -> pd.DataFrame:
    # Ensure this path is correct for your environment
    return pd.read_csv(os.path.join(os.getcwd(), filename))

df = load_data('IE1.csv')

# --- MAIN DASHBOARD LOGIC ---

# Add a radio button in the sidebar for main navigation
st.sidebar.header("Navigation")
app_mode = st.sidebar.radio("Aller à", [
    "Statistiques & Techniques Générales",
    "Comparaisons Joueurs & Équipes",
    "Constructeur d'Équipe Personnalisée",
    "Explorateur de Données"
])

# --- FILTRES GÉNERAUX (APPLICABLES À TOUTES LES PAGES SAUF L'EXPLORATEUR DE DONNÉES) ---
# Ces filtres sont définis une seule fois et s'appliquent globalement si la page est liée au dashboard
if app_mode in ["Statistiques & Techniques Générales", "Comparaisons Joueurs & Équipes", "Constructeur d'Équipe Personnalisée"]:
    st.sidebar.header("Filtres généraux")

    # Fill NaN values with an empty string before sorting for these columns
    teams = st.sidebar.multiselect("Équipe", sorted(df['Team'].fillna('').unique()), default=sorted(df['Team'].fillna('').unique()))
    positions = st.sidebar.multiselect("Poste", sorted(df['Position'].fillna('').unique()), default=sorted(df['Position'].fillna('').unique()))
    elements = st.sidebar.multiselect("Élément", sorted(df['Element'].fillna('').unique()), default=sorted(df['Element'].fillna('').unique()))

    moves_cols = ['1st Move', '2nd Move', '3rd Move', '4th Move']
    selected_moves = {}
    for col in moves_cols:
        opts = sorted(df[col].dropna().fillna('').unique())
        selected = st.sidebar.multiselect(f"Sélection {col}", opts, default=opts)
        selected_moves[col] = selected

    filtered = df[
        df['Team'].isin(teams) &
        df['Position'].isin(positions) &
        df['Element'].isin(elements)
    ].copy()

    for col in moves_cols:
        sel = selected_moves[col]
        filtered = filtered[filtered[col].fillna('').isin(sel)]

    # --- SÉLECTION DES CRITÈRES DE TOP (APPLICABLE AUX PAGES DU DASHBOARD) ---
    stats_cols = ['FP', 'TP', 'Kick', 'Body', 'Control', 'Guard', 'Speed', 'Stamina', 'Guts']
    criteres = stats_cols + ['Moyenne']
    crit = st.sidebar.selectbox("Critère de classement", criteres)

    arr = filtered[stats_cols].to_numpy(dtype=float)
    arr_masked = np.ma.masked_invalid(arr)

    if crit == 'Moyenne':
        filtered['Moyenne'] = arr_masked.mean(axis=1)
        score_col = 'Moyenne'
    else:
        score_col = crit

    st.title(f"**{len(filtered)} joueurs**")

    st.sidebar.markdown("---") # Séparateur visuel


if app_mode == "Statistiques & Techniques Générales":
    st.title("Statistiques et Techniques Générales")
    # --- TOP 5 JOUEURS ---
    st.subheader(f"Top 5 joueurs selon **{score_col}**")
    top5_joueurs = filtered.nlargest(5, score_col)[['Name', 'Team', 'Position', score_col]]
    st.table(top5_joueurs)

    # --- TOP 5 ÉQUIPES ---
    st.subheader(f"Top 5 équipes selon moyenne de **{score_col}**")
    top5_equipes = filtered.groupby('Team')[score_col].mean().nlargest(5).reset_index()
    st.table(top5_equipes)

    # --- UTILISATION TECHNIQUE ---
    st.subheader("Techniques les plus utilisées")
    all_moves = pd.concat([filtered[c] for c in moves_cols])
    move_counts = all_moves.value_counts().head(10)
    st.bar_chart(move_counts)

    # --- VISUALISATIONS ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Répartition par Postes")
        fig1, ax1 = plt.subplots()
        sns.countplot(y='Position', data=filtered, order=filtered['Position'].value_counts().index,
                      palette='viridis', hue='Position', legend=False, ax=ax1)
        st.pyplot(fig1)
    with col2:
        st.subheader("Répartition par Éléments")
        fig2, ax2 = plt.subplots()
        sns.countplot(y='Element', data=filtered, order=filtered['Element'].value_counts().index,
                      palette='coolwarm', hue='Element', legend=False, ax=ax2)
        st.pyplot(fig2)

elif app_mode == "Comparaisons Joueurs & Équipes":
    st.title("Comparaisons de Joueurs et Profils d'Équipes")
    # --- RADARS COMPARATIFS ---
    st.subheader("Diagrammes radar : Comparaisons & Équipe")

    col_radar_left, col_radar_right = st.columns(2)

    with col_radar_left:
        st.subheader("🏋️ Comparaison entre deux joueurs")
        cols_compare = st.columns(2)
        with cols_compare[0]:
            joueur1 = st.selectbox("Choisir le joueur 1", sorted(filtered['Name'].unique()), key='joueur1_comp')
        with cols_compare[1]:
            joueur2 = st.selectbox("Choisir le joueur 2", sorted(filtered['Name'].unique()), key='joueur2_comp')

        if joueur1 and joueur2:
            j1_stats = filtered[filtered['Name'] == joueur1][stats_cols].iloc[0]
            j2_stats = filtered[filtered['Name'] == joueur2][stats_cols].iloc[0]

            labels = stats_cols
            values1 = (j1_stats / 100 * 100).tolist()
            values2 = (j2_stats / 100 * 100).tolist()
            values1 += values1[:1]
            values2 += values2[:1]
            angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
            angles += angles[:1]

            fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
            ax.plot(angles, values1, label=joueur1, color='green')
            ax.fill(angles, values1, alpha=0.2, color='green')
            ax.plot(angles, values2, label=joueur2, color='red')
            ax.fill(angles, values2, alpha=0.2, color='red')
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels)
            ax.set_yticklabels([])
            ax.set_title(f"Comparaison entre {joueur1} et {joueur2}", size=13)

            for angle, val1, label in zip(angles, values1, labels + [labels[0]]):
                ax.text(angle, val1 + 5, f"{j1_stats[label]:.1f}", ha='center', va='center', fontsize=8, color='green')
            for angle, val2, label in zip(angles, values2, labels + [labels[0]]):
                ax.text(angle, val2 + 5, f"{j2_stats[label]:.1f}", ha='center', va='center', fontsize=8, color='red')

            ax.legend(loc='upper right')
            st.pyplot(fig)

    with col_radar_right:
        st.markdown("### Profil d'Équipe")
        equipes = filtered['Team'].fillna('').unique()
        eq = st.selectbox("Choisir une équipe pour voir son profil moyen", sorted(equipes), key="equipe_profile")

        if eq:
            eq_stats = filtered[filtered['Team'] == eq][stats_cols].mean()
            eq_norm = (eq_stats / eq_stats.max()) * 100
            values = eq_norm.tolist() + [eq_norm.tolist()[0]]
            angles = np.linspace(0, 2 * np.pi, len(stats_cols), endpoint=False).tolist()
            angles += angles[:1]

            fig_eq, ax_eq = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
            ax_eq.plot(angles, values, color='blue')
            ax_eq.fill(angles, values, alpha=0.25, color='blue')
            ax_eq.set_xticks(angles[:-1])
            ax_eq.set_xticklabels(stats_cols)
            ax_eq.set_yticklabels([])
            ax_eq.set_title(f"{eq} – Profil moyen")

            for angle, value, label in zip(angles, values, stats_cols + [stats_cols[0]]):
                ax_eq.text(angle, value + 5, f"{eq_stats[label]:.1f}", ha='center', va='center', fontsize=8)

            st.pyplot(fig_eq)

elif app_mode == "Constructeur d'Équipe Personnalisée":
    st.title("Constructeur d'Équipe Personnalisée")
    # --- RADAR ÉQUIPE PERSONNALISÉE ---
    joueurs_select = st.multiselect("Choisir plusieurs joueurs pour créer une équipe personnalisée", sorted(filtered['Name'].unique()),
                                    key="custom_team_builder")

    col_team_vis, col_team_radar = st.columns(2)

    with col_team_vis:
        if joueurs_select:
            st.markdown("### Position des joueurs sur le terrain")

            position_map = {
                'GK': [(0.5, 0.1)],
                'DF': [(0.2, 0.3), (0.4, 0.3), (0.6, 0.3), (0.8, 0.3)],
                'MF': [(0.2, 0.55), (0.4, 0.55), (0.6, 0.55), (0.8, 0.55)],
                'FW': [(0.3, 0.8), (0.5, 0.8), (0.7, 0.8)]
            }

            fig_field, ax_field = plt.subplots(figsize=(6, 8))
            fig_field.patch.set_facecolor("#4CAF50")

            ax_field.set_xlim(0, 1)
            ax_field.set_ylim(0, 1)
            ax_field.set_facecolor("#4CAF50")
            ax_field.axis("off")

            # --- DESSIN DES LIGNES DU TERRAIN DE FOOTBALL ---
            ax_field.plot([0.02, 0.98], [0.02, 0.02], color="white", linewidth=1.5)
            ax_field.plot([0.02, 0.02], [0.02, 0.5], color="white", linewidth=1.5)
            ax_field.plot([0.98, 0.98], [0.02, 0.5], color="white", linewidth=1.5)
            ax_field.plot([0.02, 0.98], [0.5, 0.5], color="white", linewidth=1.5)
            center_circle = plt.Circle((0.5, 0.5), 0.15, color='white', fill=False, linewidth=1.5)
            ax_field.add_patch(center_circle)

            ax_field.add_patch(plt.Rectangle((0.15, 0.02), 0.7, 0.16, color='white', fill=False, linewidth=1.5))
            ax_field.plot(0.5, 0.12, 'o', color='white', markersize=5)
            # --- FIN DESSIN DES LIGNES DU TERRAIN DE FOOTBALL ---

            team_df = filtered[filtered['Name'].isin(joueurs_select)].copy()

            position_order = {'GK': 0, 'DF': 1, 'MF': 2, 'FW': 3}
            team_df['Position_Order'] = team_df['Position'].fillna('Unknown').map(position_order)
            team_df = team_df.sort_values(by='Position_Order')

            used_coords_by_position = {pos: [] for pos in position_map.keys()}

            for _, row in team_df.iterrows():
                pos = row['Position']
                name = row['Name']

                coords_list = position_map.get(pos, [])
                chosen_coords = None

                for x, y in coords_list:
                    if (x, y) not in used_coords_by_position[pos]:
                        chosen_coords = (x, y)
                        used_coords_by_position[pos].append((x, y))
                        break

                if chosen_coords:
                    x, y = chosen_coords
                    ax_field.plot(x, y, 'o', color='gold', markersize=15, markeredgecolor='black', markeredgewidth=1)
                    ax_field.text(x, y + 0.03, name, color='white', ha='center', va='bottom', fontsize=9, weight='bold',
                                  bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', boxstyle='round,pad=0.2'))
                else:
                    st.warning(
                        f"Impossible de placer le joueur {name} ({pos}). Il n'y a plus de place disponible pour ce poste ou le poste est inconnu.")

            st.pyplot(fig_field)

    with col_team_radar:
        if joueurs_select:
            team_df = filtered[filtered['Name'].isin(joueurs_select)]
            team_stats = team_df[stats_cols].mean()
            team_norm = (team_stats / team_stats.max()) * 100

            values = team_norm.tolist() + [team_norm.tolist()[0]]
            angles = np.linspace(0, 2 * np.pi, len(stats_cols), endpoint=False).tolist()
            angles += angles[:1]

            fig_custom, ax_custom = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
            ax_custom.plot(angles, values, color="purple")
            ax_custom.fill(angles, values, alpha=0.25, color="purple")
            ax_custom.set_xticks(angles[:-1])
            ax_custom.set_xticklabels(stats_cols)
            ax_custom.set_yticklabels([])
            ax_custom.set_title("Équipe personnalisée – Profil moyen")

            for angle, value, label in zip(angles, values, stats_cols + [stats_cols[0]]):
                ax_custom.text(angle, value + 5, f"{team_stats[label]:.1f}", ha='center', va='center', fontsize=8,
                               color="purple")

            st.pyplot(fig_custom)

    # --- EXPORT CSV FILTRÉ (Disponibles sur toutes les pages du Dashboard) ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 Exporter les Données Filtrées")
    csv = filtered.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("Télécharger CSV", csv, "filtered_IE1.csv", "text/csv")


elif app_mode == "Explorateur de Données":
    st.title("Explorateur de Données")
    st.subheader("Filtrer et explorer toutes les données des joueurs")

    # Filters for the Data Explorer
    explorer_teams = st.multiselect(
        "Filtrer par équipe",
        sorted(df['Team'].fillna('').unique()),
        key='explorer_teams_filter'
    )
    explorer_names = st.multiselect(
        "Filtrer par nom de joueur",
        sorted(df['Name'].unique()),
        key='explorer_names_filter'
    )

    explorer_filtered_df = df.copy()

    if explorer_teams:
        explorer_filtered_df = explorer_filtered_df[explorer_filtered_df['Team'].fillna('').isin(explorer_teams)]
    if explorer_names:
        explorer_filtered_df = explorer_filtered_df[explorer_filtered_df['Name'].isin(explorer_names)]

    st.write(f"Affichage de **{len(explorer_filtered_df)}** joueurs sur **{len(df)}**")
    st.dataframe(explorer_filtered_df)

    csv_explorer = explorer_filtered_df.to_csv(index=False).encode('utf-16')
    st.download_button(
        label="Télécharger les données filtrées",
        data=csv_explorer,
        file_name="explored_IE1_data.csv",
        mime="text/csv",
    )