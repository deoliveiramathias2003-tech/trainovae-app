#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 21:03:12 2026

@author: deoliveira_mathias
"""

import streamlit as st
import requests
from google import genai

# --- 1. CONFIGURATION DE LA PAGE WEB ---
st.set_page_config(page_title="Trainovae", page_icon="🏃‍♂️", layout="centered")

st.title("🏃‍♂️ Trainovae : Ton Coach Sportif IA")
st.markdown("Connecte ton compte Strava et obtiens un plan d'entraînement sur-mesure généré par l'Intelligence Artificielle.")

# --- 2. BARRE LATÉRALE (Inputs utilisateur) ---
st.sidebar.header("⚙️ Configuration")
strava_token = st.sidebar.text_input("Jeton Strava (Access Token)", type="password")
gemini_key = st.sidebar.text_input("Clé API Google Gemini", type="password")
objectif = st.sidebar.text_area("Ton objectif sportif", "Préparer un 10 km en moins de 40 minutes")

# --- 3. BOUTON D'ACTION ---
if st.button("🚀 Analyser mon entraînement", type="primary"):
    
    # Vérification que l'utilisateur a bien rempli ses clés
    if not strava_token or not gemini_key:
        st.error("⚠️ Oups ! Il manque ton jeton Strava ou ta clé Gemini dans la barre latérale.")
    else:
        with st.spinner("📡 Connexion à Strava en cours..."):
            
            # --- 4. RÉCUPÉRATION STRAVA ---
            url_strava = "https://www.strava.com/api/v3/athlete/activities"
            reponse_strava = requests.get(url_strava, headers={"Authorization": f"Bearer {strava_token}"}, params={"per_page": 5})
            
            if reponse_strava.status_code == 200:
                activites = reponse_strava.json()
                resume_activites = ""
                charge_totale_km = 0
                charge_totale_min = 0
                
                for act in activites:
                    nom = act.get('name', 'Inconnu')
                    distance = act.get('distance', 0) / 1000
                    temps_min = act.get('moving_time', 0) / 60
                    
                    charge_totale_km += distance
                    charge_totale_min += temps_min
                    
                    fc_moyenne = act.get('average_heartrate', 'Non mesurée')
                    
                    allure_str = ""
                    if distance > 0:
                        allure_dec = temps_min / distance
                        min_allure = int(allure_dec)
                        sec_allure = int((allure_dec - min_allure) * 60)
                        allure_str = f"{min_allure}:{sec_allure:02d} /km"
                    
                    resume_activites += f"- {distance:.1f} km en {temps_min:.0f} min (Allure: {allure_str}, FC: {fc_moyenne})\n"
                
                st.success("✅ Données Strava récupérées avec succès !")
                
                # Affichage de belles jauges pour les statistiques
                st.subheader("📊 Ton volume récent (5 dernières séances)")
                col1, col2 = st.columns(2)
                col1.metric("Distance Cumulée", f"{charge_totale_km:.1f} km")
                col2.metric("Temps d'effort", f"{charge_totale_min:.0f} min")

                # --- 5. ANALYSE IA ---
                with st.spinner("🧠 Ton coach IA étudie ton dossier..."):
                    client = genai.Client(api_key=gemini_key)
                    
                    prompt_coach = f"""Tu es un Head Coach sportif expert en périodisation.
                    Objectif de l'athlète : "{objectif}".
                    Charge récente : {charge_totale_km:.1f} km en {charge_totale_min:.0f} minutes.
                    Détail des 5 séances :
                    {resume_activites}
                    
                    1. Évalue brièvement sa charge d'entraînement par rapport à son objectif.
                    2. Propose-lui un programme ultra-précis pour ses 2 prochaines séances (échauffement, corps de séance, récupération). Format clair et lisible.
                    """

                    try:
                        reponse_ia = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_coach)
                        
                        st.divider()
                        st.subheader("🏆 Ton Plan Adaptatif")
                        st.info(reponse_ia.text)
                        
                    except Exception as e:
                        st.error(f"⚠️ Erreur de l'IA : {e}")

            else:
                st.error(f"⚠️ Erreur Strava (Code {reponse_strava.status_code}). Ton jeton a peut-être expiré !")