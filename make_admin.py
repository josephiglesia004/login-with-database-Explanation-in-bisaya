"""
make_admin.py
-------------
DUPLICATE nga kopya (Bisaya nga paliwanag).
Himoon nga admin ang usa ka existing nga account.

Paggamit:
    python make_admin.py <username-o-email>

Pananglitan:
    python make_admin.py joseph
    python make_admin.py joseph@email.com
"""

import sys  # Para makabasa sa arguments gikan sa command line.

import firebase_db  # Ang atong Firebase functions.


def main():
    # sys.argv = listahan sa gi-type sa command line.
    # sys.argv[0] = ngalan sa script; sys.argv[1] = username/email.
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <username-or-email>")
        return 1  # Kulang o sobra ang argument.

    target = sys.argv[1].strip().lower()  # Tangtangon space, himoon lowercase.
    firebase_db.init_firebase(force=True)  # Pugson pag-connect sa Firebase.

    if not firebase_db.is_ready():
        print("Can't connect to Firebase:", firebase_db.get_error())
        return 1

    match = None  # Dinhi ibutang ang nakit-an nga profile.
    for profile in firebase_db.list_profiles():
        # Itandi sa username o email (case-insensitive).
        if (
            (profile.get("username_lower") or "").lower() == target
            or (profile.get("email") or "").lower() == target
        ):
            match = profile
            break  # Hunong na kay nakit-an na.

    if match is None:
        print(f"No account found for “{target}”.")
        return 1

    if match.get("role") == "admin":
        # Admin na daan - walay buhaton.
        print(f"{match.get('username')} ({match.get('email')}) is already an admin.")
        return 0

    firebase_db.set_role(match["uid"], "admin")  # Ilisan ang role ngadto sa admin.
    print(f"{match.get('username')} ({match.get('email')}) is now an admin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
