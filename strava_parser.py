#!/usr/bin/env python3
"""
Client Strava API avec authentification OAuth2
Récupère et analyse les activités sportives de l'utilisateur pour l'année en cours.

Auteur: Assistant IA
Date: 2025
"""

import requests
import pandas as pd
import json
import time
import webbrowser
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class StravaAPIClient:
    """Client pour interagir avec l'API Strava en utilisant OAuth2."""
    
    # URLs de l'API Strava
    BASE_URL = "https://www.strava.com/api/v3"
    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialise le client Strava.
        
        Args:
            client_id: ID client de l'application Strava
            client_secret: Secret client de l'application Strava
            redirect_uri: URI de redirection après authentification
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
    def get_authorization_url(self, scopes: List[str] = None) -> str:
        """
        Génère l'URL d'autorisation pour l'authentification OAuth2.
        
        Args:
            scopes: Liste des permissions demandées (par défaut: read,activity:read)
        
        Returns:
            URL d'autorisation Strava
        """
        if scopes is None:
            scopes = ["read", "activity:read"]
        
        scope_string = ",".join(scopes)
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope_string,
            "approval_prompt": "auto"
        }
        
        # Construire l'URL avec les paramètres
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{self.AUTH_URL}?{param_string}"
        
        return auth_url
    
    def exchange_token(self, authorization_code: str) -> Dict:
        """
        Échange le code d'autorisation contre des tokens d'accès.
        
        Args:
            authorization_code: Code d'autorisation reçu après authentification
        
        Returns:
            Dictionnaire contenant les tokens et informations d'expiration
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Stocker les tokens
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]
            self.token_expires_at = token_data["expires_at"]
            
            print("✅ Tokens obtenus avec succès!")
            print(f"Token expire le: {datetime.fromtimestamp(self.token_expires_at)}")
            
            return token_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de l'échange du token: {e}")
            if hasattr(e.response, 'text'):
                print(f"Réponse: {e.response.text}")
            raise
    
    def refresh_access_token(self) -> Dict:
        """
        Rafraîchit le token d'accès en utilisant le refresh token.
        
        Returns:
            Dictionnaire contenant les nouveaux tokens
        """
        if not self.refresh_token:
            raise ValueError("Aucun refresh token disponible")
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Mettre à jour les tokens
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]
            self.token_expires_at = token_data["expires_at"]
            
            print("✅ Token rafraîchi avec succès!")
            return token_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors du rafraîchissement du token: {e}")
            raise
    
    def _ensure_valid_token(self):
        """Vérifie et rafraîchit le token si nécessaire."""
        if not self.access_token:
            raise ValueError("Aucun token d'accès disponible. Authentifiez-vous d'abord.")
        
        # Vérifier si le token expire dans moins d'une heure
        current_time = time.time()
        if self.token_expires_at and (self.token_expires_at - current_time) < 3600:
            print("🔄 Token expire bientôt, rafraîchissement...")
            self.refresh_access_token()
    
    def _make_authenticated_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Effectue une requête authentifiée à l'API Strava.
        
        Args:
            endpoint: Point de terminaison de l'API (ex: "/athlete")
            params: Paramètres de la requête
        
        Returns:
            Réponse JSON de l'API
        """
        self._ensure_valid_token()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur lors de la requête API: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Code de statut: {e.response.status_code}")
                print(f"Réponse: {e.response.text}")
            raise
    
    def get_athlete_info(self) -> Dict:
        """
        Récupère les informations de l'athlète connecté.
        
        Returns:
            Dictionnaire contenant les informations de l'athlète
        """
        return self._make_authenticated_request("/athlete")
    
    def get_activities(self, after: Optional[datetime] = None, 
                      before: Optional[datetime] = None, 
                      per_page: int = 50) -> List[Dict]:
        """
        Récupère les activités de l'athlète.
        
        Args:
            after: Date de début (incluse)
            before: Date de fin (exclue)
            per_page: Nombre d'activités par page (max 200)
        
        Returns:
            Liste des activités
        """
        activities = []
        page = 1
        
        while True:
            params = {
                "per_page": min(per_page, 200),  # Limite API: 200
                "page": page
            }
            
            if after:
                params["after"] = int(after.timestamp())
            if before:
                params["before"] = int(before.timestamp())
            
            print(f"📥 Récupération page {page}...")
            page_activities = self._make_authenticated_request("/athlete/activities", params)
            
            if not page_activities:
                break
                
            activities.extend(page_activities)
            page += 1
            
            # Pause pour respecter les limites de l'API
            time.sleep(0.1)
        
        print(f"✅ {len(activities)} activités récupérées")
        return activities
    
    def get_current_year_activities(self) -> List[Dict]:
        """
        Récupère toutes les activités de l'année en cours.
        
        Returns:
            Liste des activités de l'année courante
        """
        current_year = datetime.now().year
        start_of_year = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        end_of_year = datetime(current_year + 1, 1, 1, tzinfo=timezone.utc)
        
        print(f"🗓️ Récupération des activités pour l'année {current_year}")
        return self.get_activities(after=start_of_year, before=end_of_year)
    
    def activities_to_dataframe(self, activities: List[Dict]) -> pd.DataFrame:
        """
        Convertit la liste d'activités en DataFrame pandas.
        
        Args:
            activities: Liste des activités de l'API Strava
        
        Returns:
            DataFrame pandas avec les données d'activités
        """
        if not activities:
            return pd.DataFrame()
        
        # Extraire les données importantes
        data = []
        for activity in activities:
            # Traiter la date
            start_date = pd.to_datetime(activity.get('start_date_local', activity.get('start_date')))
            
            # Calculer la vitesse moyenne (m/s vers km/h)
            distance_m = activity.get('distance', 0)
            moving_time_s = activity.get('moving_time', 1)  # Éviter division par zéro
            avg_speed_kmh = (distance_m / 1000) / (moving_time_s / 3600) if moving_time_s > 0 else 0
            
            # Construire l'enregistrement
            record = {
                'id': activity.get('id'),
                'date': start_date.date() if start_date else None,
                'nom': activity.get('name', 'Sans nom'),
                'type': activity.get('type', 'Inconnu'),
                'sport_type': activity.get('sport_type', activity.get('type', 'Inconnu')),
                'distance_km': round(distance_m / 1000, 2) if distance_m else 0,
                'duree_minutes': round(moving_time_s / 60, 1) if moving_time_s else 0,
                'vitesse_moyenne_kmh': round(avg_speed_kmh, 1),
                'denivele_positif_m': activity.get('total_elevation_gain', 0),
                'kudos_count': activity.get('kudos_count', 0),
                'calories': activity.get('calories'),
                'average_heartrate': activity.get('average_heartrate'),
                'max_heartrate': activity.get('max_heartrate'),
                'commute': activity.get('commute', False),
                'trainer': activity.get('trainer', False),
                'start_latitude': activity.get('start_latlng')[0] if activity.get('start_latlng') else None,
                'start_longitude': activity.get('start_latlng')[1] if activity.get('start_latlng') else None
            }
            data.append(record)
        
        # Créer le DataFrame
        df = pd.DataFrame(data)
        
        # Optimiser les types de données
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['commute'] = df['commute'].astype(bool)
            df['trainer'] = df['trainer'].astype(bool)
        
        return df
    
    def save_tokens(self, filepath: str = "strava_tokens.json"):
        """
        Sauvegarde les tokens dans un fichier JSON.
        
        Args:
            filepath: Chemin du fichier de sauvegarde
        """
        if self.access_token and self.refresh_token:
            token_data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.token_expires_at
            }
            
            with open(filepath, 'w') as f:
                json.dump(token_data, f)
            print(f"💾 Tokens sauvegardés dans {filepath}")
    
    def load_tokens(self, filepath: str = "strava_tokens.json") -> bool:
        """
        Charge les tokens depuis un fichier JSON.
        
        Args:
            filepath: Chemin du fichier de sauvegarde
        
        Returns:
            True si les tokens ont été chargés avec succès
        """
        try:
            with open(filepath, 'r') as f:
                token_data = json.load(f)
            
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data["refresh_token"]
            self.token_expires_at = token_data["expires_at"]
            
            print(f"📁 Tokens chargés depuis {filepath}")
            return True
            
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            print(f"⚠️ Impossible de charger les tokens depuis {filepath}")
            return False


def display_activity_summary(df: pd.DataFrame):
    """
    Affiche un résumé statistique des activités.
    
    Args:
        df: DataFrame contenant les activités
    """
    if df.empty:
        print("📊 Aucune activité trouvée pour l'analyse.")
        return
    
    print("\n" + "="*50)
    print("📊 RÉSUMÉ STATISTIQUE DES ACTIVITÉS")
    print("="*50)
    
    # Statistiques générales
    total_activities = len(df)
    total_distance = df['distance_km'].sum()
    total_time = df['duree_minutes'].sum()
    total_elevation = df['denivele_positif_m'].sum()
    
    print(f"🏃 Nombre total d'activités: {total_activities}")
    print(f"📏 Distance totale: {total_distance:.1f} km")
    print(f"⏱️ Temps total: {total_time/60:.1f} heures ({total_time:.0f} minutes)")
    print(f"⛰️ Dénivelé total: {total_elevation:.0f} m")
    
    if total_time > 0:
        avg_speed = total_distance / (total_time / 60)
        print(f"🚀 Vitesse moyenne globale: {avg_speed:.1f} km/h")
    
    # Répartition par type d'activité
    print(f"\n📋 RÉPARTITION PAR TYPE D'ACTIVITÉ:")
    activity_summary = df.groupby('type').agg({
        'distance_km': ['count', 'sum'],
        'duree_minutes': 'sum'
    }).round(1)
    
    activity_summary.columns = ['Nombre', 'Distance_km', 'Durée_min']
    print(activity_summary)
    
    # Records personnels
    print(f"\n🏆 RECORDS:")
    if not df.empty:
        longest_activity = df.loc[df['distance_km'].idxmax()]
        fastest_activity = df.loc[df['vitesse_moyenne_kmh'].idxmax()]
        
        print(f"🥇 Plus longue distance: {longest_activity['distance_km']:.1f} km")
        print(f"   └─ {longest_activity['nom']} ({longest_activity['date']})")
        print(f"⚡ Vitesse maximale: {fastest_activity['vitesse_moyenne_kmh']:.1f} km/h")
        print(f"   └─ {fastest_activity['nom']} ({fastest_activity['date']})")
    
    # Activité par mois
    if 'date' in df.columns:
        df_monthly = df.set_index('date').resample('M').agg({
            'distance_km': 'sum',
            'duree_minutes': 'sum'
        }).round(1)
        
        print(f"\n📅 ACTIVITÉ PAR MOIS:")
        for month, data in df_monthly.iterrows():
            if data['distance_km'] > 0:
                month_str = month.strftime('%Y-%m')
                print(f"   {month_str}: {data['distance_km']:.1f} km en {data['duree_minutes']/60:.1f}h")


def interactive_auth_flow(client: StravaAPIClient) -> str:
    """
    Gère le flux d'authentification interactif.
    
    Args:
        client: Instance du client Strava
    
    Returns:
        Code d'autorisation obtenu
    """
    # Générer et afficher l'URL d'autorisation
    auth_url = client.get_authorization_url(["read", "activity:read_all"])
    
    print("\n" + "="*60)
    print("🔐 AUTHENTIFICATION STRAVA REQUISE")
    print("="*60)
    print("1. Une page web va s'ouvrir pour l'authentification Strava")
    print("2. Connectez-vous et autorisez l'application")
    print("3. Vous serez redirigé vers une page (qui peut afficher une erreur)")
    print("4. Copiez le code depuis l'URL de redirection")
    print("\n📋 URL d'autorisation:")
    print(auth_url)
    
    # Ouvrir automatiquement dans le navigateur
    try:
        webbrowser.open(auth_url)
        print("✅ Page d'authentification ouverte dans votre navigateur")
    except:
        print("⚠️ Impossible d'ouvrir automatiquement le navigateur")
        print("   Veuillez copier et coller l'URL ci-dessus dans votre navigateur")
    
    # Demander le code d'autorisation
    print("\n" + "-"*60)
    print("Après authentification, vous serez redirigé vers une URL comme:")
    print(f"{client.redirect_uri}?state=&code=VOTRE_CODE_ICI&scope=read,activity:read_all")
    print("-"*60)
    
    while True:
        auth_code = input("\n🔑 Collez le code d'autorisation (ou l'URL complète): ").strip()
        
        if not auth_code:
            continue
            
        # Si l'utilisateur colle l'URL complète, extraire le code
        if auth_code.startswith('http'):
            try:
                parsed_url = urlparse(auth_code)
                query_params = parse_qs(parsed_url.query)
                if 'code' in query_params:
                    auth_code = query_params['code'][0]
                    print(f"✅ Code extrait: {auth_code[:20]}...")
                else:
                    print("❌ Aucun code trouvé dans l'URL")
                    continue
            except Exception as e:
                print(f"❌ Erreur lors du parsing de l'URL: {e}")
                continue
        
        if len(auth_code) > 10:  # Validation basique
            return auth_code
        else:
            print("❌ Code trop court, veuillez vérifier")


def main():
    """Fonction principale du script."""
    print("🚴 CLIENT STRAVA API - RÉCUPÉRATION DES ACTIVITÉS")
    print("="*55)
    
    # Configuration - Chargée depuis les variables d'environnement
    from dotenv import load_dotenv
    load_dotenv()
    
    CLIENT_ID = os.environ.get('STRAVA_CLIENT_ID', "145566")  # Valeur par défaut pour compatibilité
    CLIENT_SECRET = os.environ.get('STRAVA_CLIENT_SECRET', "d0949d11cf40903f77545b4646893c7876133585")  # Valeur par défaut pour compatibilité
    REDIRECT_URI = os.environ.get('STRAVA_REDIRECT_URI', "http://localhost")  # URL de redirection
    
    # Vérification de la configuration
    if CLIENT_ID == "VOTRE_CLIENT_ID_ICI" or CLIENT_SECRET == "VOTRE_CLIENT_SECRET_ICI":
        print("❌ CONFIGURATION REQUISE:")
        print("   Veuillez modifier les variables CLIENT_ID et CLIENT_SECRET")
        print("   avec vos identifiants d'application Strava.")
        print("\n📖 Pour obtenir ces identifiants:")
        print("   1. Allez sur https://developers.strava.com/")
        print("   2. Créez une application")
        print("   3. Notez votre Client ID et Client Secret")
        return
    
    # Initialiser le client
    client = StravaAPIClient(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    
    try:
        # Tentative de chargement des tokens existants
        if not client.load_tokens():
            print("\n🔄 Première authentification requise...")
            
            # Processus d'authentification interactif
            auth_code = interactive_auth_flow(client)
            
            # Échange du code contre des tokens
            print("\n🔄 Échange du code d'autorisation...")
            client.exchange_token(auth_code)
            
            # Sauvegarder les tokens
            client.save_tokens()
        
        # Vérifier l'authentification
        print("\n🔍 Vérification de l'authentification...")
        athlete_info = client.get_athlete_info()
        print(f"✅ Connecté en tant que: {athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}")
        
        # Récupérer les activités de l'année courante
        print(f"\n📥 Récupération des activités...")
        activities = client.get_current_year_activities()
        
        if not activities:
            print("📭 Aucune activité trouvée pour cette année.")
            return
        
        # Convertir en DataFrame
        print("🔄 Conversion en DataFrame pandas...")
        df_activities = client.activities_to_dataframe(activities)
        
        # Afficher un aperçu des données
        print(f"\n📋 APERÇU DES DONNÉES:")
        print(f"Colonnes: {list(df_activities.columns)}")
        print(f"\nPremières activités:")
        print(df_activities.head().to_string(index=False))
        
        # Afficher le résumé statistique
        display_activity_summary(df_activities)
        
        # Sauvegarder les données
        output_file = f"activites_strava_{datetime.now().year}.csv"
        df_activities.to_csv(output_file, index=False)
        print(f"\n💾 Données sauvegardées dans: {output_file}")
        
        print(f"\n✅ Script terminé avec succès!")
        print(f"📊 {len(activities)} activités traitées et analysées.")
        
    except KeyboardInterrupt:
        print("\n⏹️ Script interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

