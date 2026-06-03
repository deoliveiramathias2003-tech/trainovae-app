import streamlit as st
import requests
from google import genai

# --- 1. CONFIGURATION DE LA PAGE WEB ---
st.set_page_config(page_title="Trainovae", page_icon="🏃‍♂️", layout="centered")

st.title("🏃‍♂️ Trainovae : Ton Coach Sportif IA")
st.markdown("Connecte ton compte Strava et obtiens un plan d'entraînement sur-mesure généré par l'Intelligence Artificielle.")

# --- 2. SÉCURITÉ ET VARIABLES (Le Coffre-Fort) ---
CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
CLE_GEMINI = st.secrets["GEMINI_API_KEY"]
REDIRECT_URI = "https://trainovae-app-aigmt6xjy2y3jpjzjdbhro.streamlit.app"

# Lien officiel pour envoyer l'utilisateur vers Strava
AUTH_URL = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&approval_prompt=force&scope=activity:read_all"

# Initialisation de la mémoire de l'application
if 'access_token' not in st.session_state:
    st.session_state['access_token'] = None

# --- 3. LE MOTEUR OAUTH 2.0 (Invisible pour l'utilisateur) ---
# On regarde s'il y a un mot "code" dans l'URL (ce qui veut dire que Strava nous a renvoyé l'utilisateur)
query_params = st.query_params
if "code" in query_params and st.session_state['access_token'] is None:
    code_strava = query_params["code"]
    
    # On échange discrètement ce code contre le Jeton
    url_token = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code_strava,
        'grant_type': 'authorization_code'
    }
    reponse_echange = requests.post(url_token, data=payload)
    
    if reponse_echange.status_code == 200:
        # On sauvegarde le jeton dans la mémoire de la page
        st.session_state['access_token'] = reponse_echange.json()['access_token']
        # On nettoie l'URL pour faire propre
        st.query_params.clear()
        st.success("✅ Connexion à Strava réussie !")
    else:
        st.error("⚠️ Erreur lors de l'authentification avec Strava.")

# --- 4. L'INTERFACE UTILISATEUR ---
st.sidebar.header("⚙️ Configuration")
objectif = st.sidebar.text_area("Ton objectif sportif", "Préparer un 10 km en moins de 40 minutes")

# Si on n'a pas encore le jeton, on affiche le bouton de connexion Strava
if st.session_state['access_token'] is None:
    st.warning("👋 Pour commencer, tu dois connecter ton compte Strava.")
    # Le fameux bouton magique !
    st.link_button("🟧 Se connecter avec Strava", AUTH_URL)

# Si on a le jeton, on affiche l'analyse IA
else:
    if st.button("🚀 Analyser mon entraînement", type="primary"):
        with st.spinner("📡 Extraction de tes données biométriques..."):
            
            url_strava = "https://www.strava.com/api/v3/athlete/activities"
            reponse_strava = requests.get(url_strava, headers={"Authorization": f"Bearer {st.session_state['access_token']}"}, params={"per_page": 5})
            
            if reponse_strava.status_code == 200:
                activites = reponse_strava.json()
                resume_activites = ""
                charge_totale_km = 0
                charge_totale_min = 0
                
                for act in activites:
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
                
                st.subheader("📊 Ton volume récent (5 dernières séances)")
                col1, col2 = st.columns(2)
                col1.metric("Distance Cumulée", f"{charge_totale_km:.1f} km")
                col2.metric("Temps d'effort", f"{charge_totale_min:.0f} min")

                with st.spinner("🧠 Ton coach IA Trainovae prépare ton plan..."):
                    client = genai.Client(api_key=CLE_GEMINI)
                    
                    prompt_coach = f"""Tu es un Head Coach sportif expert en périodisation.
                    Objectif de l'athlète : "{objectif}".
                    Charge récente : {charge_totale_km:.1f} km en {charge_totale_min:.0f} minutes.
                    Détail des 5 séances :
                    {resume_activites}
                    
                    1. Évalue brièvement sa charge d'entraînement.
                    2. Propose-lui un programme ultra-précis pour ses 2 prochaines séances.
                    """

                    try:
                        reponse_ia = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_coach)
                        st.divider()
                        st.subheader("🏆 Ton Plan Adaptatif Trainovae")
                        st.info(reponse_ia.text)
                        
                    except Exception as e:
                        st.error(f"⚠️ Erreur de l'IA : {e}")
            else:
                st.error("⚠️ Erreur de récupération des données Strava.")
