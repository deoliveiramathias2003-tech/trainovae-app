import streamlit as st
import requests
from google import genai

# --- 1. CONFIGURATION DE LA PAGE WEB ---
st.set_page_config(page_title="Trainovae", page_icon="🏃‍♂️", layout="centered")

# --- 2. SÉCURITÉ ET VARIABLES ---
CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
CLE_GEMINI = st.secrets["GEMINI_API_KEY"]
REDIRECT_URI = "https://trainovae-app-aigmt6xjy2y3jpjzjdbhro.streamlit.app"

AUTH_URL = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&approval_prompt=force&scope=activity:read_all"

if 'access_token' not in st.session_state:
    st.session_state['access_token'] = None

# --- 3. LE MOTEUR OAUTH 2.0 ---
query_params = st.query_params
if "code" in query_params and st.session_state['access_token'] is None:
    code_strava = query_params["code"]
    
    url_token = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code_strava,
        'grant_type': 'authorization_code'
    }
    reponse_echange = requests.post(url_token, data=payload)
    
    if reponse_echange.status_code == 200:
        st.session_state['access_token'] = reponse_echange.json()['access_token']
        st.query_params.clear()
    else:
        st.error("⚠️ Erreur lors de l'authentification avec Strava.")

# --- 4. L'INTERFACE UTILISATEUR ---
if st.session_state['access_token'] is None:
    st.title("🏃‍♂️ Trainovae : Ton Coach Sportif IA")
    st.markdown("Connecte ton compte Strava et obtiens un plan d'entraînement sur-mesure.")
    st.warning("👋 Pour commencer, tu dois connecter ton compte Strava.")
    st.link_button("🟧 Se connecter avec Strava", AUTH_URL)

else:
    # ✨ NOUVEAU : Récupération du profil public de l'athlète ✨
    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    reponse_athlete = requests.get("https://www.strava.com/api/v3/athlete", headers=headers)
    
    prenom_athlete = "Athlète" # Valeur par défaut
    
    if reponse_athlete.status_code == 200:
        donnees_athlete = reponse_athlete.json()
        prenom_athlete = donnees_athlete.get('firstname', 'Athlète')
        photo_url = donnees_athlete.get('profile', '')
        
        # Affichage du profil (Photo + Bonjour)
        col_img, col_txt = st.columns([1, 4])
        with col_img:
            # On vérifie qu'il a bien une vraie photo de profil, sinon on ne met rien
            if photo_url and photo_url != "avatar/athlete/large.png":
                st.image(photo_url, width=80)
        with col_txt:
            st.title(f"👋 Bienvenue, {prenom_athlete} !")

    st.sidebar.header("⚙️ Configuration")
    objectif = st.sidebar.text_area("Ton objectif sportif", "Préparer un 10 km en moins de 40 minutes")

    if st.button("🚀 Analyser mon entraînement", type="primary"):
        with st.spinner("📡 Extraction de tes données biométriques..."):
            
            url_strava = "https://www.strava.com/api/v3/athlete/activities"
            reponse_strava = requests.get(url_strava, headers=headers, params={"per_page": 5})
            
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
                
                st.subheader("📊 Ton volume récent")
                col1, col2 = st.columns(2)
                col1.metric("Distance Cumulée", f"{charge_totale_km:.1f} km")
                col2.metric("Temps d'effort", f"{charge_totale_min:.0f} min")

                with st.spinner(f"🧠 Ton coach prépare le plan de {prenom_athlete}..."):
                    client = genai.Client(api_key=CLE_GEMINI)
                    
                    # ✨ NOUVEAU : Le prompt intègre le prénom pour s'adresser directement à lui ✨
                    prompt_coach = f"""Tu es le Head Coach sportif de l'application Trainovae.
                    Ton athlète s'appelle {prenom_athlete}. Adresse-toi directement à lui par son prénom de manière motivante.
                    Objectif de {prenom_athlete} : "{objectif}".
                    Charge récente : {charge_totale_km:.1f} km en {charge_totale_min:.0f} minutes.
                    Détail des 5 séances :
                    {resume_activites}
                    
                    1. Évalue brièvement sa charge d'entraînement.
                    2. Propose-lui un programme ultra-précis pour ses 2 prochaines séances.
                    Sois direct, pro, et tutelle-le/la."""

                    try:
                        reponse_ia = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_coach)
                        st.divider()
                        st.subheader("🏆 Ton Plan Adaptatif Trainovae")
                        st.info(reponse_ia.text)
                        
                    except Exception as e:
                        st.error(f"⚠️ Erreur de l'IA : {e}")
            else:
                st.error("⚠️ Erreur de récupération des données Strava.")
