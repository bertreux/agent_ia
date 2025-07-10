import streamlit as st
import joblib

model = joblib.load("regression.joblib")

st.title("Prédiction du prix d'une maison")

taille = st.number_input("Taille de la maison (en m²)", min_value=0.0, step=1.0)
nb_chambres = st.number_input("Nombre de chambres", min_value=0, step=1)
jardin = st.number_input("Présence d’un jardin (1 pour oui, 0 pour non)", min_value=0, max_value=1, step=1)

if st.button("Prédire le prix"):
    features = [[taille, nb_chambres, jardin]]
    prediction = model.predict(features)
    st.write(f"Prix estimé de la maison : {prediction[0]:.2f} €")
