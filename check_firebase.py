"""
check_firebase.py
-----------------
DUPLICATE nga kopya (Bisaya nga paliwanag).
Susihon kung husto ba ang setup sa Firebase antes padaganon ang app.

Padaganon:
    python check_firebase.py

Magpakita og [OK] kung maayo ang tanan, ug [X] nga naay tambag
kung naay kulang.
"""

# ---------------------------------------------------------------------------
# MGA IMPORT
# ---------------------------------------------------------------------------

import json  # Para makabasa sa .json file (serviceAccountKey.json).
import os  # Para makabasa sa environment variables.
import sys  # Para makakuha sa exit code (sys.exit).
from pathlib import Path  # Para susihon kung naa ba ang file.

from dotenv import load_dotenv  # Para mabasa ang .env.

import requests  # Para makatawag sa Firebase REST API.

load_dotenv()  # Basaha ang .env file.

OK = "[OK]"  # Simbolo kung successful.
FAIL = "[X]"  # Simbolo kung naay problema.


def line(status, message):
    # Moprint og usa ka linya nga naay status ug mensahe.
    print(f" {status} {message}")


def main():
    print("\n=== Firebase setup checker ===\n")
    problems = []  # Listahan sa mga problema nga nakit-an.

    # 1) .env file
    if Path(".env").exists():
        line(OK, ".env file found.")
    else:
        line(FAIL, "No .env file. Run: Copy-Item .env.example .env")
        problems.append("env")

    # 2) service account key
    # Kuhaon ang path sa key; default kay serviceAccountKey.json.
    key_file = Path(os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json"))
    project_id = None
    if not key_file.exists():
        line(FAIL, f"Service account key not found: {key_file}")
        line(" ", "Firebase Console -> Project settings -> Service accounts -> Generate new private key")
        problems.append("key")
    else:
        try:
            # Basahon ang JSON ug kuhaon ang project_id.
            info = json.loads(key_file.read_text(encoding="utf-8"))
            project_id = info.get("project_id")
            line(OK, f"Service account key found. Project: {project_id}")
        except (ValueError, OSError) as error:
            # ValueError = dili valid nga JSON; OSError = dili mabasa ang file.
            line(FAIL, f"Can't read {key_file}: {error}")
            problems.append("key")

    # 3) web api key
    api_key = os.getenv("FIREBASE_API_KEY", "").strip()
    # Sigurohon nga naa ug dili placeholder ang API key.
    if api_key and api_key != "ilagay-ang-web-api-key":
        line(OK, "FIREBASE_API_KEY found.")
    else:
        line(FAIL, "FIREBASE_API_KEY is missing from .env.")
        line(" ", "Firebase Console -> Project settings -> General -> Web API key")
        problems.append("api_key")

    if problems:  # Kung naay problema, hunong na dinhi.
        print("\nSetup is incomplete. Follow the steps in README.md.\n")
        return 1  # Exit code 1 = naay error.

    # 4) Firestore + Auth connection
    print("\n--- Testing the connection ---\n")
    try:
        import firebase_admin
        from firebase_admin import auth, credentials, firestore

        try:
            firebase_admin.get_app()  # Kung naa nay app...
        except ValueError:
            # ...kung wala pa, i-initialize gamit ang key file.
            firebase_admin.initialize_app(credentials.Certificate(str(key_file)))

        # Sulayan basahon ang "users" collection (usa lang ka document).
        snapshots = firestore.client().collection("users").limit(1).get()
        total = len(list(snapshots))
        line(OK, f"Connected to Firestore. Users docs read: {total}")
    except Exception as error:  # noqa: BLE001
        line(FAIL, f"Firestore error: {error}")
        line(" ", "Have you created the Firestore Database in the Firebase Console?")
        return 1

    try:
        # Sulayan listahan ang users sa Authentication (max 1 lang).
        users = list(auth.list_users(max_results=1).iterate_all())
        line(OK, f"Connected to Authentication. Users: {len(users)} (max 1 checked)")
    except Exception as error:  # noqa: BLE001
        line(FAIL, f"Authentication error: {error}")
        return 1

    # 5) Naka-enable ba ang Email/Password sign-in?
    try:
        # Sulayan mag-login gamit ang fake account.
        # Kung "OPERATION_NOT_ALLOWED" ang error, off ang Email/Password.
        response = requests.post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
            params={"key": api_key},
            json={
                "email": "check@example.com",
                "password": "hindi-totoong-password",
                "returnSecureToken": True,
            },
            timeout=15,
        )
        code = ""
        try:
            code = response.json().get("error", {}).get("message", "")
        except ValueError:
            pass

        if code == "OPERATION_NOT_ALLOWED":
            line(FAIL, "Email/Password sign-in is OFF.")
            line(" ", "Firebase Console -> Authentication -> Sign-in method -> Email/Password -> Enable")
            return 1
        if code in {"EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"}:
            # Kini nga error kay normal lang kay fake ang account -
            # nagpasabot nga naka-enable ang Email/Password.
            line(OK, "Email/Password sign-in is enabled.")
        elif code:
            line(" ", f"Note: the sign-in test returned {code}")
    except requests.RequestException:
        line(FAIL, "Can't reach Firebase Authentication. Check your internet connection.")
        return 1

    print("\nAll good! You can now run: python app.py\n")
    return 0  # Exit code 0 = successful.


if __name__ == "__main__":
    # sys.exit = ibalik ang exit code sa operating system.
    sys.exit(main())
