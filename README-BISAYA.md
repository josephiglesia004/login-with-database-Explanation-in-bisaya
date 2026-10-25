# Joseph.login with database — Bisaya nga Giya

Kini nga folder (`joseph-bisaya`) kay **duplicate** sa original nga project
(`C:\Users\suete\Documents\joseph`). Pareho ra sila og code ug pareho og
Firebase project, pero **ang tanan nga file dinhi kay naay Bisaya nga
paliwanag sa matag linya o block**.

> Importante: wala giusab ang original nga folder. Kung naay mabali dinhi,
> safe gihapon ang original nga system.

---

## 1. Unsa ang kinahanglan

- **Python** (ang original nga `.venv` pwede magamit)
- **Firebase project** nga naay:
  - Authentication → Email/Password nga naka-enable
  - Cloud Firestore nga nahimo na
  - Service account key (`serviceAccountKey.json`)
  - Web API key (`FIREBASE_API_KEY` sa `.env`)

Ang duplicate kay wala nay kaugalingong `.venv`, pero makagamit siya sa
original nga virtual environment.

---

## 2. Setup sa Firebase Console (step by step)

1. Adto sa <https://console.firebase.google.com>.
2. Pilia ang project (sa ato kay `joseph-database`).
3. **Authentication** → **Sign-in method** → **Email/Password** → **Enable**.
4. **Firestore Database** → **Create database** (kung wala pa).
5. **Project settings** (gear icon) → **Service accounts** →
   **Generate new private key**.
6. I-rename ang na-download nga file ngadto sa `serviceAccountKey.json`
   ug ibutang sa sulod niini nga folder.
7. **Project settings** → **General** → **Web API Key** →
   ibutang sa `.env` isip `FIREBASE_API_KEY`.

**Ayaw i-post o i-share ang `serviceAccountKey.json`.** Kini kay full access
sa tibuok Firebase project.

---

## 3. Setup sa computer

### 3.1 Gamita ang original nga virtual environment

```powershell
cd C:\Users\suete\Documents\joseph-bisaya

# Susihon kung husto ang Firebase setup
C:\Users\suete\Documents\joseph\.venv\Scripts\python.exe check_firebase.py
```

Kung mogawas ang `All good!`, padagana na ang app:

```powershell
C:\Users\suete\Documents\joseph\.venv\Scripts\python.exe app.py
```

Dayon ablihi ang <http://127.0.0.1:5000>.

### 3.2 Kung occupied ang port 5000

```powershell
C:\Users\suete\Documents\joseph\.venv\Scripts\python.exe -m flask --app app run --port 5001
```

Dayon ablihi ang <http://127.0.0.1:5001>.

### 3.3 Kung gusto og kaugalingong `.venv`

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python check_firebase.py
python app.py
```

---

## 4. Unsa ang mahitabo inig register ug login

### Register (`/register`)

1. Ang user mo-submit og full name, username, email, ug password.
2. Ang `app.py` mo-validate: gitas-on sa username, valid nga email,
   pareho ba ang password ug confirmation.
3. Susihon kung gamit na ang username (`username_lower` sa Firestore).
4. Kung **wala pay admin**, ang bag-ong account mahimong **admin**.
   Kung naa nay admin, **user** ang bag-ong account.
5. Himoon ang account sa **Firebase Authentication** (`create_user`).
6. Himoon ang profile sa **Firestore**: `users/{uid}` nga naay username,
   full name, email, role, ug `created_at`.
7. Kung mapakyas ang pag-save sa profile, burahon usab ang Auth account
   (rollback) para walay account nga walay profile.

### Login (`/login`)

1. Pwede mag-login gamit ang **username** o **email**.
2. Kung username, pangitaon sa Firestore ang email niini.
3. Mag-sign in sa Firebase gamit ang email ug password.
4. Himoon nga **secure session cookie** ang `idToken`
   (`create_session_cookie`), nga molungtad og **5 ka adlaw**.
5. Ang session cookie gitipigan sa Flask session (HttpOnly).
6. Dad-on ang user sa **dashboard**.

### Matag protected page

- Ang `login_required` decorator mo-verify sa session cookie gamit ang
  Firebase (`verify_session_cookie`, `check_revoked=True`).
- Kung expired o revoked, limpyohan ang session ug ibalik sa login page.
- Ang `admin_required` mo-check usab kung `role == "admin"`.

### Logout (`/logout`)

- I-revoke ang tanang refresh tokens (`revoke_refresh_tokens`).
- Limpyohan ang Flask session.
- Ibalik sa login page.

### Settings (`/settings`)

- **Profile** — usbon ang full name ug username (dili pwede usbon dinhi
  ang email kay naka-link sa Firebase Authentication).
- **Password** — kinahanglan i-verify una ang current password, dayon
  himoon og bag-ong session para dili ma-logout ang user.
- **Log out of all devices** — revoke tanang session.

---

## 5. Mga file ug unsa ang ilang trabaho

| File | Unsa ang trabaho |
| --- | --- |
| `app.py` | Ang Flask app: routes, validation, login/register, admin, settings |
| `firebase_db.py` | Tanang Firebase functions (Auth + Firestore + session) |
| `check_firebase.py` | Nagsusi kung husto ba ang setup |
| `make_admin.py` | Himoon nga admin ang existing nga account |
| `templates/` | Mga HTML pages |
| `static/style.css` | Tanang design, apil ang gold theme |
| `static/auth.js` | Show/Hide password |
| `static/ui.js` | Confirm dialogs ug Copy buttons |
| `static/admin.js` | Live search sa admin table |
| `.env` | `SECRET_KEY` ug `FIREBASE_API_KEY` |
| `serviceAccountKey.json` | Secret sa Firebase (ayaw i-share) |

---

## 6. Asa ang Bisaya nga paliwanag

Ang mga comment gibutang gayud sa tupad sa code:

- **Python** (`app.py`, `firebase_db.py`, `check_firebase.py`,
  `make_admin.py`) — `#` ang sinugdanan sa comment.
- **HTML templates** — `{# ... #}` ang Jinja comment. Wala kini makita
  sa browser.
- **JavaScript** (`auth.js`, `ui.js`, `admin.js`) — `//` ang comment.
- **CSS** (`style.css`) — `/* ... */` ang comment, naa sa matag section.

Mga example sa syntax nga gipasabot sa comments:

```python
# Python: dictionary
user = {"username": "juan", "role": "admin"}
```

```jinja
{# Jinja: ipakita ang variable #}
{{ user.username }}
```

```javascript
// JavaScript: pangitaa ang elemento pinaagi sa ID
var search = document.getElementById("user-search");
```

```css
/* CSS: class selector */
.btn { color: #fff; }
```

---

## 7. Roles ug proteksyon

- **user** — makita lang ang iyang kaugalingong dashboard ug settings.
- **admin** — makasulod sa `/admin` ug makahimo sa:
  - tan-aw sa tanang account ug stats
  - promote/demote
  - delete account

Proteksyon nga naa na:

- Dili puwede usbon o burahon ang kaugalingong role/account sa admin panel.
- Dili puwede i-demote o burahon ang **katapusang admin**.
- Ang role check kay **server-side** (Firestore profile), dili lang sa UI.

Kung gusto himoon nga admin ang existing account:

```powershell
C:\Users\suete\Documents\joseph\.venv\Scripts\python.exe make_admin.py <username-o-email>
```

---

## 8. Troubleshooting

| Problema | Solusyon |
| --- | --- |
| “Firebase isn't set up yet” | Kulang ang `serviceAccountKey.json` o `FIREBASE_API_KEY` sa `.env` |
| `API key not valid` | Sayop ang `FIREBASE_API_KEY`; kopyaha pag-usab sa Project settings → General |
| `403` / `PERMISSION_DENIED` sa Firestore | Wala pa nahimo ang Firestore database |
| `auth/operation-not-allowed` | Wala pa naka-enable ang Email/Password |
| Kalit lang nag-logout | 5 ka adlaw ang session (`SESSION_DAYS` sa `firebase_db.py`) |
| Dili mo-open ang page | Naay laing app sa port 5000; gamit og `--port 5001` |

---

## 9. Seguridad

- Usba ang `SECRET_KEY` sa `.env` ngadto sa taas ug random nga string.
- Ang `.env` ug `serviceAccountKey.json` kay naa sa `.gitignore`.
- Ayaw i-commit o i-post kining duha.
- Kung na-leak ang service account key, **i-rotate** kini sa Firebase Console
  (bag-ong key, dayon delete ang daan).
