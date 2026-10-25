"""
firebase_db.py
--------------
DUPLICATE nga kopya (Bisaya nga paliwanag).
Tanang Firebase (Authentication + Cloud Firestore) nga gikinahanglan sa app.

Kinahanglan og service account key (default: serviceAccountKey.json) ug ang
Web API key sa Firebase project (FIREBASE_API_KEY sa .env).
"""

# ---------------------------------------------------------------------------
# MGA IMPORT
# ---------------------------------------------------------------------------

import os  # Para makabasa og environment variables (.env).
import time  # Para makakuha og oras (gamit sa cooldown sa pag-connect).
from datetime import timedelta  # Para sa gitas-on sa session (5 ka adlaw).
from pathlib import Path  # Para susihon kung naa ba ang file (serviceAccountKey.json).

import firebase_admin  # Ang main Firebase Admin SDK.
import requests  # Para makatawag sa Firebase REST API (login).
from dotenv import load_dotenv  # Para mabasa ang .env file.
from firebase_admin import auth, credentials, firestore  # Mga bahin sa Firebase.
from google.cloud.firestore_v1.base_query import FieldFilter  # Para sa where() query.

load_dotenv()  # Basaha ang .env ug ibutang sa environment variables.

# Kuhaon ang path sa credentials; default kay serviceAccountKey.json.
CREDENTIALS_FILE = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
# Kuhaon ang Web API key sa Firebase (gikinahanglan sa login).
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")

# Ang URL sa Firebase REST API para sa email/password login.
SIGN_IN_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
SESSION_DAYS = 5  # Gitas-on sa session: 5 ka adlaw.
VALID_ROLES = {"admin", "user"}  # Ang duha lang ka valid nga role.

# Internal nga estado sa connection.
_ready = False  # True kung connected na sa Firebase.
_error = ""  # Error message kung napakyas.
_last_attempt = 0.0  # Oras sa katapusang pagsulay (para sa cooldown).


# ---------------------------------------------------------------------------
# MGA CUSTOM EXCEPTION
# Exception = klase sa error nga atong kaugalingon nga gihimo.
# ---------------------------------------------------------------------------


class FirebaseSetupError(RuntimeError):
    """Kulang ang settings o wala ang service account key."""


class InvalidLogin(Exception):
    """Sayop ang username/email o password."""

    def __init__(self, message):
        super().__init__(message)  # Tawgon ang parent Exception.
        self.message = message  # Tipigan ang mensahe para magamit sa app.py.


# ---------------------------------------------------------------------------
# PAG-INITIALIZE SA FIREBASE
# ---------------------------------------------------------------------------


def init_firebase(force=False):
    """I-initialize ang Firebase Admin SDK ug i-test ang Firestore.

    Mobalik dayon kung ready na, ug naay 15-second cooldown antes mosulay
    pag-usab kung napakyas (para dili mohinay ang matag request).
    """
    global _ready, _error, _last_attempt  # Pwede bag-uhon ang global variables.

    now = time.monotonic()  # Oras karon (monotonic = dili moatras).
    if not force:  # Kung dili pinugos...
        if _ready:
            return True  # ...ug ready na, ayaw na usba.
        if now - _last_attempt < 15:  # ...ug wala pa 15 ka segundo...
            return False  # ...ayaw pa mosulay (cooldown).

    _last_attempt = now  # Itala ang oras sa pagsulay.

    try:
        # Susihon kung naa ba ang service account key file.
        if not Path(CREDENTIALS_FILE).exists():
            raise FirebaseSetupError(
                f"Service account key not found ({CREDENTIALS_FILE}). "
                "Download it from Firebase Console -> Project settings -> Service accounts."
            )
        # Susihon kung naa ba ang API key.
        if not FIREBASE_API_KEY:
            raise FirebaseSetupError(
                "FIREBASE_API_KEY is missing from .env. Get it from "
                "Firebase Console -> Project settings -> General -> Web API Key."
            )

        try:
            firebase_admin.get_app()  # Sulayan kung naa nay existing app.
        except ValueError:
            # Kung wala pa, i-initialize gamit ang credentials file.
            firebase_admin.initialize_app(credentials.Certificate(CREDENTIALS_FILE))

        # Sulayan basahon ang Firestore para masuta kung naka-enable ba.
        get_db().collection("users").limit(1).get()

        _ready = True  # Successful ang connection.
        _error = ""  # Walay error.
        print("[Firebase] Connection to Authentication and Firestore is OK.")
    except Exception as error:  # noqa: BLE001 - gusto natong ipakita tanang error sa page
        _ready = False
        _error = str(error)  # Tipigan ang error isip text.
        print("[Firebase] Not set up yet:", error)
    return _ready  # Ibalik kung ready ba o dili.


# ---------------------------------------------------------------------------
# MGA GAMAY NGA HELPER
# ---------------------------------------------------------------------------


def is_ready():
    return _ready  # True kung connected na.


def get_error():
    return _error  # Ang error message (empty string kung walay error).


def get_db():
    return firestore.client()  # Ibalik ang Firestore database client.


# --- Firestore: user profiles -------------------------------------------------
# Ang "users" collection kay nagtipig sa profile sa matag account.
# Ang document ID niini kay ang Firebase UID.


def find_profile_by_username(username):
    """Pangitaa ang profile gamit ang username (case-insensitive). None kung wala."""
    snapshots = (
        get_db()
        .collection("users")  # Adto sa "users" collection.
        .where(filter=FieldFilter("username_lower", "==", username.strip().lower()))  # Itandi lowercase.
        .limit(1)  # Usa lang ka resulta.
        .get()  # Ipadagan ang query.
    )
    for snapshot in snapshots:  # Kung naay resulta...
        profile = snapshot.to_dict() or {}  # Himoon nga dictionary.
        profile["uid"] = snapshot.id  # Ang document ID kay ang UID.
        return profile  # Ibalik ang profile.
    return None  # Wala nakit-an.


def get_profile(uid):
    snapshot = get_db().collection("users").document(uid).get()  # Kuhaon ang document.
    if not snapshot.exists:  # Kung wala ang profile...
        return None
    profile = snapshot.to_dict() or {}  # Himoon nga dictionary.
    profile["uid"] = snapshot.id  # Idugang ang UID.
    profile.setdefault("role", "user")  # Kung walay role, "user".
    return profile


def list_profiles():
    """Tanang user profiles, pinakabag-o una."""
    profiles = []
    for snapshot in get_db().collection("users").stream():  # Basaha tanan documents.
        profile = snapshot.to_dict() or {}
        profile["uid"] = snapshot.id
        profile.setdefault("role", "user")
        profiles.append(profile)  # Idugang sa listahan.

    def sort_key(profile):
        # Gamit ang timestamp sa created_at para ma-sort.
        created = profile.get("created_at")
        return created.timestamp() if hasattr(created, "timestamp") else 0

    profiles.sort(key=sort_key, reverse=True)  # reverse=True = pinakabag-o una.
    return profiles


def count_admins():
    # Ihap ang tanang profile nga ang role kay "admin".
    return sum(1 for profile in list_profiles() if profile.get("role") == "admin")


def set_role(uid, role):
    """Ilisan ang role sa user ('admin' o 'user')."""
    if role not in VALID_ROLES:  # Sigurohon nga valid.
        raise ValueError(f"Hindi valid na role: {role}")
    get_db().collection("users").document(uid).update({"role": role})  # I-update sa Firestore.


def delete_profile(uid):
    get_db().collection("users").document(uid).delete()  # Burahon ang profile document.


def update_profile(uid, fields):
    """I-update ang mga field sa profile sa Firestore."""
    if fields:  # Kung naay fields nga i-update...
        get_db().collection("users").document(uid).update(fields)


def update_auth_user(uid, **fields):
    """I-update ang Firebase Authentication record (sama sa password, display_name)."""
    return auth.update_user(uid, **fields)  # **fields = ipasa ang tanang keyword arguments.


def create_profile(uid, username, full_name, email, role="user"):
    if role not in VALID_ROLES:
        raise ValueError(f"Hindi valid na role: {role}")
    get_db().collection("users").document(uid).set(  # set() = himoon o ilisan ang document.
        {
            "username": username,
            "username_lower": username.lower(),  # Para case-insensitive ang pagpangita.
            "full_name": full_name,
            "email": email,
            "email_lower": email.lower(),
            "role": role,
            "created_at": firestore.SERVER_TIMESTAMP,  # Oras sa server (automatic).
        }
    )


# --- Firebase Authentication --------------------------------------------------


def create_auth_user(email, password, full_name):
    """Himoon ang account sa Firebase Authentication. Ibalik ang user record."""
    return auth.create_user(email=email, password=password, display_name=full_name)


def delete_auth_user(uid):
    """Rollback kung napakyas ang pag-save sa profile sa Firestore."""
    auth.delete_user(uid)


def sign_in_with_password(email, password):
    """Mag-login sa Firebase Auth gamit ang REST API. Ibalik ang idToken ug localId."""
    try:
        response = requests.post(  # POST request sa Firebase login endpoint.
            SIGN_IN_URL,
            params={"key": FIREBASE_API_KEY},  # Ang API key isip query parameter.
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=15,  # Ayaw paghulat labaw sa 15 ka segundo.
        )
    except requests.RequestException:
        # Network error (walay internet, etc.).
        raise InvalidLogin("Can't reach Firebase. Check your internet connection.") from None

    if response.ok:  # Kung 200 OK ang response...
        return response.json()  # ...ibalik ang JSON (naay idToken ug localId).

    code = ""
    try:
        # Kuhaon ang error code gikan sa JSON response.
        code = response.json().get("error", {}).get("message", "")
    except ValueError:
        pass  # Kung dili JSON, pasagdan lang.
    raise InvalidLogin(_friendly_sign_in_error(code))  # I-convert sa friendly nga mensahe.


def _friendly_sign_in_error(code):
    # Ang underscore sa sinugdanan (_) kay nagpasabot nga internal helper lang.
    if code in {"EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"}:
        return "Incorrect username/email or password. Try again."
    if code == "USER_DISABLED":
        return "This account has been disabled. Contact an admin."
    if code == "TOO_MANY_ATTEMPTS_TRY_LATER":
        return "Too many attempts. Please wait a few minutes."
    if code:
        return f"Can't log in ({code})."
    return "Can't log in. Please try again."


def create_session_cookie(id_token):
    """Himoon nga secure session cookie ang idToken (server-side session)."""
    # expires_in = pila ka adlaw molungtad ang cookie.
    return auth.create_session_cookie(id_token, expires_in=timedelta(days=SESSION_DAYS))


def verify_session_cookie(session_cookie):
    """I-verify ang session cookie. Mag-error kung invalid o revoked."""
    # check_revoked=True = susihon kung gi-logout ba sa laing device.
    return auth.verify_session_cookie(session_cookie, check_revoked=True)


def revoke_sessions(uid):
    """Puwersahang mag-logout sa tanang device (revoke refresh tokens)."""
    auth.revoke_refresh_tokens(uid)
