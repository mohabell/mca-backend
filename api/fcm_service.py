# # ============================================================
# # api/fcm_service.py
# # Envoie des notifications push via Firebase Cloud Messaging
# # ============================================================

# import requests
# import json
# import logging
# from decouple import config

# logger = logging.getLogger(__name__)

# # Clé serveur Firebase depuis .env
# FCM_SERVER_KEY = config('FCM_SERVER_KEY', default='cf08c32ac8107ac4cd53cbf4aec8e82953271352')

# FCM_URL = 'https://fcm.googleapis.com/fcm/send'


# def envoyer_push(token_appareil: str, titre: str, message: str, data: dict = None):
#     """
#     Envoie une notification push à UN appareil Android.

#     token_appareil : le token FCM de l'utilisateur (stocké en base)
#     titre          : titre de la notification (ex: "Nouveau chantier assigné")
#     message        : corps du message
#     data           : données supplémentaires optionnelles (dict)
#     """
#     if not token_appareil:
#         logger.warning("envoyer_push: token vide, notification ignorée.")
#         return False

#     if FCM_SERVER_KEY == 'cf08c32ac8107ac4cd53cbf4aec8e82953271352':
#         logger.warning("envoyer_push: clé serveur Firebase non configurée !")
#         return False

#     headers = {
#         'Authorization': f'key={FCM_SERVER_KEY}',
#         'Content-Type': 'application/json',
#     }

#     payload = {
#         'to': token_appareil,
#         'notification': {
#             'title': titre,
#             'body':  message,
#             'sound': 'default',
#         },
#         'android': {
#             'priority': 'high',
#             'notification': {
#                 'channel_id': 'mca_notifications',
#                 'sound':      'default',
#                 'priority':   'high',
#             },
#         },
#     }

#     # Ajouter des données supplémentaires si fourni
#     if data:
#         payload['data'] = data

#     try:
#         response = requests.post(FCM_URL, headers=headers, data=json.dumps(payload), timeout=10)
#         result = response.json()

#         if response.status_code == 200 and result.get('success') == 1:
#             logger.info(f"Push envoyé avec succès à {token_appareil[:20]}...")
#             return True
#         else:
#             logger.error(f"Erreur FCM: {result}")
#             return False

#     except requests.exceptions.RequestException as e:
#         logger.error(f"Erreur réseau FCM: {e}")
#         return False


# def envoyer_push_multiple(tokens: list, titre: str, message: str, data: dict = None):
#     """
#     Envoie une notification push à PLUSIEURS appareils en une seule requête.
#     Utilise 'registration_ids' au lieu de 'to'.
#     """
#     if not tokens:
#         return False

#     if FCM_SERVER_KEY == 'REMPLACE_PAR_TA_CLE_SERVEUR_FIREBASE':
#         logger.warning("envoyer_push_multiple: clé serveur Firebase non configurée !")
#         return False

#     # FCM accepte max 1000 tokens par requête
#     tokens = [t for t in tokens if t]  # Supprimer les tokens vides
#     if not tokens:
#         return False

#     headers = {
#         'Authorization': f'key={FCM_SERVER_KEY}',
#         'Content-Type': 'application/json',
#     }

#     payload = {
#         'registration_ids': tokens,
#         'notification': {
#             'title': titre,
#             'body':  message,
#             'sound': 'default',
#         },
#         'android': {
#             'priority': 'high',
#             'notification': {
#                 'channel_id': 'mca_notifications',
#                 'sound':      'default',
#                 'priority':   'high',
#             },
#         },
#     }

#     if data:
#         payload['data'] = data

#     try:
#         response = requests.post(FCM_URL, headers=headers, data=json.dumps(payload), timeout=10)
#         result = response.json()
#         logger.info(f"Push multiple: {result.get('success')} succès, {result.get('failure')} échec")
#         return result.get('success', 0) > 0

#     except requests.exceptions.RequestException as e:
#         logger.error(f"Erreur réseau FCM multiple: {e}")
#         return False






# ============================================================
# api/fcm_service.py — API FCM V1
# ============================================================

import requests
import json
import logging
import os
from google.oauth2 import service_account
import google.auth.transport.requests

logger = logging.getLogger(__name__)

# Fichier JSON téléchargé depuis Firebase Console
# → Comptes de service → Générer une nouvelle clé privée
# SERVICE_ACCOUNT_FILE = 'firebase-service-account.json'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'firebase-service-account.json')

# Ton Project ID Firebase (visible dans l'URL Firebase)
PROJECT_ID = 'fir-chantiers'

FCM_URL = f'https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send'


def get_access_token():
    """Génère un token Google valide pour l'API FCM V1."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/firebase.messaging']
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token


class UnregisteredTokenError(Exception):
    """Exception levée quand le token FCM n'est plus valide (UNREGISTERED)."""
    pass

def envoyer_push(token_appareil: str, titre: str, message: str, data: dict = None):
    if not token_appareil:
        print("⚠️  Token vide — notification ignorée.")
        return False

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ Fichier {SERVICE_ACCOUNT_FILE} introuvable dans backend/")
        return False

    try:
        access_token = get_access_token()
    except Exception as e:
        print(f"❌ Erreur token Google: {e}")
        return False

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'message': {
            'token': token_appareil,
            'notification': {
                'title': titre,
                'body':  message,
            },
            'android': {
                'priority': 'high',
                'notification': {
                    'channel_id':              'mca_notifications',
                    'sound':                   'default',
                    'default_vibrate_timings': True,
                    'visibility':              'PUBLIC',
                },
            },
        }
    }

    if data:
        payload['message']['data'] = {k: str(v) for k, v in data.items()}

    try:
        response = requests.post(FCM_URL, headers=headers, data=json.dumps(payload), timeout=10)
        result = response.json()

        if response.status_code == 200:
            print(f"✅ Push envoyé avec succès !")
            return True
        else:
            # Gérer le cas spécifique du token expiré/désinscrit
            if response.status_code == 404:
                error = result.get('error', {})
                if error.get('status') == 'NOT_FOUND' or 'UNREGISTERED' in str(result):
                    print(f"🗑️  Token invalide détecté (UNREGISTERED).")
                    raise UnregisteredTokenError("Token unregistered")
            
            print(f"❌ Erreur FCM ({response.status_code}): {result}")
            return False

    except UnregisteredTokenError:
        raise
    except Exception as e:
        print(f"❌ Erreur réseau FCM: {e}")
        return False


def envoyer_push_multiple(tokens: list, titre: str, message: str, data: dict = None):
    tokens = [t for t in tokens if t]
    if not tokens:
        return False
    results = [envoyer_push(token, titre, message, data) for token in tokens]
    return any(results)