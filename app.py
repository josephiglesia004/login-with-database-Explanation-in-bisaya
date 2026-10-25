"""
app.py
------
DUPLICATE nga kopya (Bisaya nga paliwanag).
Login system nga Flask + Firebase (Authentication ug Cloud Firestore).

Unsaon pagpadagan:
    python app.py   ->   http://127.0.0.1:5000

Basaha ang README-BISAYA.md para sa setup sa Firebase
(serviceAccountKey.json ug FIREBASE_API_KEY sa .env).
"""

# ---------------------------------------------------------------------------
# MGA IMPORT
# Ang "import" kay mokuha og code gikan sa laing file o library.
# ---------------------------------------------------------------------------

import os  # "os" = makabasa sa environment variables (sama sa .env) ug sa OS.
from datetime import datetime, timedelta, timezone  # Mga gamit sa petsa ug oras.
from functools import wraps  # "wraps" = motipig sa pangalan sa function kung maghimo tag decorator.

# Kini nga block kay nag-import og mga bahin sa Flask.
# Ang "from ... import ..." kay mokuha lang sa gikinahanglan, dili tibuok library.
from flask import (
    Flask,  # Ang Flask mismo - mao ang naghimo sa web app.
    flash,  # "flash" = temporary nga mensahe (sama sa "Login successful").
    g,  # "g" = storage nga molungtad lang sa usa ka request (sama sa g.uid).
    redirect,  # "redirect" = mobalhin sa laing page.
    render_template,  # "render_template" = mopakita sa HTML file gikan sa templates/.
    request,  # "request" = datos nga gipadala sa browser (form, method, etc.).
    session,  # "session" = datos nga gitipigan sa browser pinaagi sa cookie.
    url_for,  # "url_for" = mokuha sa URL sa usa ka route pinaagi sa ngalan niini.
)
from firebase_admin import auth  # "auth" = Firebase Authentication (paghimo/login sa account).
from google.api_core.exceptions import GoogleAPICallError  # Error type kung mapakyas ang tawag sa Google/Firebase.

import firebase_db  # Ang atong kaugalingon nga file nga naay tanang Firebase functions.

# ---------------------------------------------------------------------------
# PAGHIMO SA APP
# ---------------------------------------------------------------------------

app = Flask(__name__)  # Naghimo og Flask app. Ang __name__ kay nagpaila asa ang app.

# Ang secret_key kay ginagamit sa pag-encrypt sa session cookie.
# "os.getenv" = kuhaon ang SECRET_KEY sa .env; kung wala, gamiton ang default.
app.secret_key = os.getenv("SECRET_KEY", "palitan-ito-ng-random-secret-key")

# Ang session kay molungtad og 5 ka adlaw (gikuha sa firebase_db.SESSION_DAYS).
app.permanent_session_lifetime = timedelta(days=firebase_db.SESSION_DAYS)

# Kalagayan sa Firebase connection (para sa friendly nga error sa page).
# "force=True" = pugson ang pag-connect bisan bag-o pa lang nagsugod ang app.
firebase_db.init_firebase(force=True)
firebase_ready = firebase_db.is_ready()  # True kung connected, False kung dili.
firebase_error = firebase_db.get_error()  # Ang error message kung napakyas.


# ---------------------------------------------------------------------------
# BEFORE_REQUEST: modagan ni sa TANANG request antes sa route
# ---------------------------------------------------------------------------


@app.before_request  # Decorator: nag-ingon nga modagan ni antes sa matag request.
def retry_firebase_connection():
    """Kung wala pa naka-setup sa pagsugod, sulayan pag-usab panagsa."""
    global firebase_ready, firebase_error  # "global" = pwede bag-uhon ang gawas nga variable.
    if not firebase_ready:  # Kung dili pa connected...
        firebase_db.init_firebase()  # ...sulayan pag-connect usab (naay 15s cooldown sa sulod).
        firebase_ready = firebase_db.is_ready()  # I-update ang status.
        firebase_error = firebase_db.get_error()  # I-update ang error message.


# ---------------------------------------------------------------------------
# CONTEXT PROCESSOR: nagdugang og variables sa TANANG template
# ---------------------------------------------------------------------------


@app.context_processor  # Kini nga function kay automatic nga magamit sa HTML templates.
def inject_globals():
    # "return" = ibalik ang dictionary; ang keys kay mahimo nang variable sa HTML.
    return {
        "firebase_ready": firebase_ready,  # Pwede gamiton sa HTML: {{ firebase_ready }}
        "firebase_error": firebase_error,  # Error message kung naa.
        "current_year": datetime.now().year,  # Tuig karon (para sa footer).
        "is_admin": getattr(g, "is_admin", False),  # True kung admin ang naka-login.
        "current_uid": getattr(g, "uid", None),  # UID sa naka-login (None kung wala).
    }
    # "getattr(g, 'is_admin', False)" = kuhaon ang g.is_admin; kung wala, False ang default.


# ---------------------------------------------------------------------------
# DECORATOR: login_required
# Kini ang nagabantay nga ang user naka-login antes makasulod sa page.
# ---------------------------------------------------------------------------


def login_required(view):
    """I-redirect sa login page kung walay valid nga Firebase session."""

    @wraps(view)  # Tipigan ang original nga pangalan ug docstring sa view.
    def wrapped(*args, **kwargs):  # Ang *args/**kwargs = bisan unsang arguments sa route.
        cookie = session.get("session_cookie")  # Kuhaon ang session cookie sa browser session.
        claims = None  # Sugod nga walay verified user info.
        if cookie:  # Kung naay cookie...
            try:
                # I-verify sa Firebase kung tinuod ug valid pa ang cookie.
                claims = firebase_db.verify_session_cookie(cookie)
            except Exception:  # expired, revoked, o dili ma-verify
                claims = None  # Kung naay error, ituring nga wala naka-login.

        if not claims:  # Kung walay valid claims (wala naka-login)...
            session.clear()  # ...limpyohan ang session.
            flash("Please log in first.", "warning")  # Pahinumdom sa user.
            return redirect(url_for("login"))  # Dad-on sa login page.

        # Kung valid ang login, i-save ang info sa "g" para magamit sa route.
        g.uid = claims["uid"]  # UID = unique ID sa Firebase user.
        g.claims = claims  # Tibuok claims (email, auth_time, etc.).
        g.profile = firebase_db.get_profile(g.uid) or {}  # Profile sa Firestore (o empty dict).
        g.profile.setdefault("role", "user")  # Kung walay role, "user" ang default.
        g.is_admin = g.profile.get("role") == "admin"  # True kung admin.
        return view(*args, **kwargs)  # Padayon sa orihinal nga route function.

    return wrapped  # Ibalik ang wrapped function aron magamit isip decorator.


# ---------------------------------------------------------------------------
# DECORATOR: admin_required
# Admin lang ang makasulod niini nga mga page.
# ---------------------------------------------------------------------------


def admin_required(view):
    """Admin lang ang puwedeng mosulod. I-redirect ang normal users sa dashboard."""

    @wraps(view)
    @login_required  # Unahon ang login check, dayon ang admin check.
    def wrapped(*args, **kwargs):
        if not g.is_admin:  # Kung dili admin...
            flash("Only admins can access that page.", "warning")
            return redirect(url_for("dashboard"))  # ...ibalik sa dashboard.
        return view(*args, **kwargs)  # Kung admin, padayon.

    return wrapped


# ---------------------------------------------------------------------------
# ROUTE: "/" (dashboard)
# Ang @app.route("/") kay nag-ingon nga kini ang home page.
# ---------------------------------------------------------------------------


@app.route("/")
@login_required  # Kinahanglan naka-login.
def dashboard():
    """Home page sa mga naka-login nga user (user o admin)."""
    profile = g.profile  # Kuhaon ang profile nga na-save sa login_required.

    last_login = None  # Sugod nga walay last login.
    if g.claims.get("auth_time"):  # "auth_time" = oras sa pag-login (Unix timestamp).
        # fromtimestamp = i-convert ang timestamp ngadto sa datetime.
        last_login = datetime.fromtimestamp(g.claims["auth_time"])

    created = profile.get("created_at")  # Petsa sa paghimo sa account.
    days_active = None
    if created:
        # Kung naay timezone ang created, gamiton ang UTC; kung wala, local time.
        now = datetime.now(timezone.utc) if getattr(created, "tzinfo", None) else datetime.now()
        # max(1, ...) = dili moubos sa 1 ang adlaw.
        days_active = max(1, (now - created).days + 1)

    hour = datetime.now().hour  # Oras karon (0-23).
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    # Dictionary sa info nga ipakita sa dashboard.html.
    user = {
        "uid": g.uid,
        "username": profile.get("username") or session.get("username", "—"),
        "full_name": profile.get("full_name") or session.get("full_name", "—"),
        "email": profile.get("email") or g.claims.get("email", "—"),
        "role": profile.get("role", "user"),
        "created_at": created,
        "last_login": last_login,
    }
    # "or" = kung walay value sa wala, gamiton ang naa sa tuo.
    return render_template(
        "dashboard.html",  # Ang HTML file nga ipakita.
        user=user,  # Ipadala ang user info.
        greeting=greeting,  # "Good morning" etc.
        days_active=days_active,  # Pila ka adlaw na ang account.
        session_days=firebase_db.SESSION_DAYS,  # 5 ka adlaw nga session.
    )


# ---------------------------------------------------------------------------
# ROUTE: settings page
# ---------------------------------------------------------------------------


@app.route("/settings")
@login_required
def settings():
    """Account settings page: profile ug password."""
    return render_template("settings.html", profile=g.profile)


# ---------------------------------------------------------------------------
# ROUTE: update profile (POST lang)
# ---------------------------------------------------------------------------


@app.route("/settings/profile", methods=["POST"])  # POST = form submission.
@login_required
def update_profile():
    """I-update ang full name ug username."""
    # .strip() = tangtangon ang space sa sinugdanan ug katapusan.
    full_name = request.form.get("full_name", "").strip()
    username = request.form.get("username", "").strip()

    errors = []  # Listahan sa mga error.
    if len(full_name) < 2:
        errors.append("Enter your full name.")
    if len(username) < 3:
        errors.append("Username must be at least 3 characters.")
    # .replace("_", "") = tangtangon ang underscore; .isalnum() = letters/numbers lang.
    if not username.replace("_", "").replace(".", "").isalnum():
        errors.append(
            "Username may only contain letters, numbers, underscores (_), and dots (.)."
        )

    if not errors:  # Kung walay error, susihon kung gamit na ang username.
        existing = firebase_db.find_profile_by_username(username)
        if existing and existing["uid"] != g.uid:  # Naay laing user nga nagamit niini.
            errors.append("That username is already taken.")

    if errors:  # Kung naay error, ipakita tanan ug balik sa settings.
        for message in errors:
            flash(message, "danger")
        return redirect(url_for("settings"))

    try:
        # I-update ang profile sa Firestore.
        firebase_db.update_profile(
            g.uid,
            {
                "username": username,
                "username_lower": username.lower(),  # Para case-insensitive ang pagpangita.
                "full_name": full_name,
            },
        )
        # I-update usab ang display name sa Firebase Authentication.
        firebase_db.update_auth_user(g.uid, display_name=full_name)
    except GoogleAPICallError as error:
        flash(f"Firebase error: {error}", "danger")
        return redirect(url_for("settings"))

    # I-update ang session para bag-o dayon ang makita sa header.
    session["username"] = username
    session["full_name"] = full_name
    flash("Your profile has been updated.", "success")
    return redirect(url_for("settings"))


# ---------------------------------------------------------------------------
# ROUTE: change password
# ---------------------------------------------------------------------------


@app.route("/settings/password", methods=["POST"])
@login_required
def update_password():
    """Ilisan ang password — kinahanglan i-verify una ang current password."""
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    errors = []
    if not current:
        errors.append("Enter your current password.")
    if len(new) < 8:
        errors.append("New password must be at least 8 characters.")
    if new != confirm:  # Dili pareho ang bag-o ug confirmation.
        errors.append("New password and confirmation don't match.")
    if new and new == current:
        errors.append("New password must be different from your current password.")

    if errors:
        for message in errors:
            flash(message, "danger")
        return redirect(url_for("settings"))

    # Kuhaon ang email sa profile o sa claims.
    email = g.profile.get("email") or g.claims.get("email")
    if not email:
        flash("Couldn't find the email for your account.", "danger")
        return redirect(url_for("settings"))

    try:
        # Sulayan pag-login gamit ang karaan nga password para ma-verify.
        firebase_db.sign_in_with_password(email, current)
    except firebase_db.InvalidLogin:
        flash("Your current password is incorrect.", "danger")
        return redirect(url_for("settings"))

    try:
        # Ilisan ang password sa Firebase Authentication.
        firebase_db.update_auth_user(g.uid, password=new)
    except GoogleAPICallError as error:
        flash(f"Firebase error: {error}", "danger")
        return redirect(url_for("settings"))

    # Kung ilisan ang password, i-invalidate sa Firebase ang karaan nga
    # session. Maghimo dayon og bag-ong session para dili ma-logout ang user.
    try:
        tokens = firebase_db.sign_in_with_password(email, new)  # Login sa bag-ong password.
        # Himoon nga session cookie ang bag-ong idToken.
        session["session_cookie"] = firebase_db.create_session_cookie(tokens["idToken"])
        session["username"] = g.profile.get("username", session.get("username", ""))
        session["full_name"] = g.profile.get("full_name", session.get("full_name", ""))
        session.permanent = True  # Himoon nga permanent (5 ka adlaw).
    except (firebase_db.InvalidLogin, GoogleAPICallError):
        # Kung napakyas ang paghimo og bag-ong session, pugson pag-logout.
        session.clear()
        flash(
            "Your password has been changed. Please log in again with your new password.",
            "success",
        )
        return redirect(url_for("login"))

    flash("Your password has been changed. Use it on your next login.", "success")
    return redirect(url_for("settings"))


# ---------------------------------------------------------------------------
# ROUTE: logout sa tanang device
# ---------------------------------------------------------------------------


@app.route("/settings/logout-all", methods=["POST"])
@login_required
def logout_all():
    """I-logout sa tanang device (revoke tanang refresh tokens)."""
    try:
        firebase_db.revoke_sessions(g.uid)  # Puwersahan pag-logout sa tanan.
    except Exception:  # ok lang bisan dili ma-revoke
        pass  # "pass" = walay buhaton, padayon lang.
    session.clear()  # Limpyohan ang session sa browser.
    flash("You've been logged out on all devices. Log in again to continue.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# ROUTE: login
# ---------------------------------------------------------------------------


@app.route("/login", methods=["GET", "POST"])  # GET = pakita page, POST = submit form.
def login():
    if session.get("session_cookie"):  # Kung naka-login na...
        return redirect(url_for("dashboard"))  # ...dili na kinahanglan mag-login usab.

    identifier = ""  # Pwede username o email.

    if request.method == "POST":  # Kung nag-submit og form...
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not firebase_ready:  # Kung wala pa naka-setup ang Firebase...
            flash("Firebase isn't set up yet. See README.md.", "warning")
            return render_template("login.html", identifier=identifier), 503  # 503 = service unavailable.

        if not identifier or not password:  # Kung kulang ang input...
            flash("Enter your username/email and password.", "danger")
            return render_template("login.html", identifier=identifier), 400  # 400 = bad request.

        try:
            if "@" in identifier:  # Kung naay @, email ang gigamit.
                email = identifier.lower()  # Himoon lowercase ang email.
            else:  # Kung wala, username ang gigamit.
                profile = firebase_db.find_profile_by_username(identifier)
                if profile is None:  # Wala nakit-an ang username.
                    flash("Incorrect username/email or password. Try again.", "danger")
                    return render_template("login.html", identifier=identifier), 401  # 401 = unauthorized.
                email = profile["email"]  # Kuhaon ang email sa profile.

            tokens = firebase_db.sign_in_with_password(email, password)  # Login sa Firebase.
            session_cookie = firebase_db.create_session_cookie(tokens["idToken"])  # Himoon session cookie.
            profile = firebase_db.get_profile(tokens["localId"])  # Kuhaon ang profile.
        except firebase_db.InvalidLogin as error:
            flash(error.message, "danger")
            return render_template("login.html", identifier=identifier), 401
        except GoogleAPICallError as error:
            flash(f"Firebase error: {error}", "danger")
            return render_template("login.html", identifier=identifier), 500  # 500 = server error.

        session.clear()  # Limpyohan ang daan nga session.
        session.permanent = True  # Permanent session (5 ka adlaw).
        session["session_cookie"] = session_cookie  # Tipigan ang session cookie.
        session["username"] = (profile or {}).get("username", identifier)  # Tipigan ang username.
        session["full_name"] = (profile or {}).get("full_name", "")  # Tipigan ang full name.

        # "f" string = pwede isulod ang variable sa text gamit {}.
        flash(f"Welcome, {session['full_name'] or session['username']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html", identifier=identifier)  # GET: ipakita ang form.


# ---------------------------------------------------------------------------
# ROUTE: register
# ---------------------------------------------------------------------------


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("session_cookie"):  # Naka-login na, dili na kinahanglan mag-register.
        return redirect(url_for("dashboard"))

    form = {"username": "", "full_name": "", "email": ""}  # Empty form para sa GET.

    if request.method == "POST":
        form["username"] = request.form.get("username", "").strip()
        form["full_name"] = request.form.get("full_name", "").strip()
        form["email"] = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not firebase_ready:
            flash("Firebase isn't set up yet. See README.md.", "warning")
            return render_template("register.html", form=form), 503

        errors = []
        if len(form["username"]) < 3:
            errors.append("Username must be at least 3 characters.")
        if not form["username"].replace("_", "").replace(".", "").isalnum():
            errors.append(
                "Username may only contain letters, numbers, underscores (_), and dots (.)."
            )
        if len(form["full_name"]) < 2:
            errors.append("Enter your full name.")
        # Susihon kung naay @ ug naay dot pagkahuman sa @ (sama sa gmail.com).
        if "@" not in form["email"] or "." not in form["email"].split("@")[-1]:
            errors.append("That email doesn't look valid.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Password and confirmation don't match.")

        if not errors:
            try:
                if firebase_db.find_profile_by_username(form["username"]):
                    errors.append("That username is already taken.")
                else:
                    # Ang unang account (walay admin pa) mahimong admin.
                    role = "admin" if firebase_db.count_admins() == 0 else "user"
                    # Himoon ang account sa Firebase Authentication.
                    auth_user = firebase_db.create_auth_user(
                        form["email"], password, form["full_name"]
                    )
                    try:
                        # Himoon ang profile sa Firestore.
                        firebase_db.create_profile(
                            auth_user.uid,
                            form["username"],
                            form["full_name"],
                            form["email"],
                            role=role,
                        )
                    except Exception:
                        # Ayaw pagbilin og account nga walay profile (rollback).
                        firebase_db.delete_auth_user(auth_user.uid)
                        raise  # "raise" = ipadayon paglabay ang error.

                    message = "Registration successful! You can log in now."
                    if role == "admin":
                        message += " You're the first account, so you're an admin."
                    flash(message, "success")
                    return redirect(url_for("login"))
            except auth.EmailAlreadyExistsError:  # Kung gamit na ang email.
                errors.append("An account with that email already exists.")
            except GoogleAPICallError as error:
                errors.append(f"Firebase error: {error}")
            except Exception as error:  # sama sa nawala ang internet samtang nag-save
                errors.append(f"Something went wrong: {error}")

        for message in errors:
            flash(message, "danger")

    return render_template("register.html", form=form)


# ---------------------------------------------------------------------------
# ROUTE: admin dashboard
# ---------------------------------------------------------------------------


@app.route("/admin")
@admin_required  # Admin lang.
def admin_users():
    """Admin dashboard: estadistika ug listahan sa tanang account."""
    profiles = firebase_db.list_profiles()  # Tanang profile sa Firestore.
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)  # Petsa 7 ka adlaw ang milabay.

    users = []
    new_users = 0
    for profile in profiles:  # Sa matag profile...
        created = profile.get("created_at")
        is_new = False
        try:
            # Bag-o kung naay created_at ug mas bag-o pa sa 7 ka adlaw.
            is_new = bool(created) and created >= week_ago
        except TypeError:
            is_new = False  # Kung dili ma-compare (hal. walay timezone), dili bag-o.
        if is_new:
            new_users += 1  # "+= 1" = dugang usa.

        # Ngalan nga ipakita: full_name, o username, o "?".
        display_name = profile.get("full_name") or profile.get("username") or "?"
        users.append(
            {
                "uid": profile["uid"],
                "username": profile.get("username", "—"),
                "full_name": profile.get("full_name", "—"),
                "email": profile.get("email", "—"),
                "role": profile.get("role", "user"),
                "created_at": created,
                "initial": display_name[:1].upper(),  # Unang letra, uppercase (para sa avatar).
            }
        )

    stats = {
        "total": len(users),  # Total nga users.
        "admins": sum(1 for user in users if user["role"] == "admin"),  # Pila ka admin.
        "new": new_users,  # Pila ka bag-o sulod sa 7 ka adlaw.
    }
    return render_template("admin.html", users=users, stats=stats)


# ---------------------------------------------------------------------------
# ROUTE: promote/demote user
# ---------------------------------------------------------------------------


@app.route("/admin/users/<uid>/role", methods=["POST"])
@admin_required
def admin_set_role(uid):  # Ang <uid> sa route kay moabot isip argument.
    """I-promote o i-demote ang usa ka user."""
    action = request.form.get("action", "")
    if action not in {"promote", "demote"}:  # Sigurohon nga valid ang action.
        flash("Invalid action.", "danger")
        return redirect(url_for("admin_users"))

    if uid == g.uid:  # Dili puwede usbon ang kaugalingong role.
        flash("You can't change your own role.", "warning")
        return redirect(url_for("admin_users"))

    profile = firebase_db.get_profile(uid)
    if profile is None:  # Wala ang user.
        flash("That user doesn't exist.", "danger")
        return redirect(url_for("admin_users"))

    role = "admin" if action == "promote" else "user"  # Tinoon ang bag-ong role.
    if (
        role == "user"  # Kung i-demote...
        and profile.get("role") == "admin"  # ...ug admin siya...
        and firebase_db.count_admins() <= 1  # ...ug siya na lang ang admin...
    ):
        flash("The last admin can't be demoted.", "warning")  # ...dili puwede.
        return redirect(url_for("admin_users"))

    try:
        firebase_db.set_role(uid, role)  # I-save ang bag-ong role.
    except GoogleAPICallError as error:
        flash(f"Firebase error: {error}", "danger")
        return redirect(url_for("admin_users"))

    # Mensahe: "username is now an admin." o "username is now a user."
    flash(
        f"{profile.get('username', uid)} is now {'an admin' if role == 'admin' else 'a user'}.",
        "success",
    )
    return redirect(url_for("admin_users"))


# ---------------------------------------------------------------------------
# ROUTE: delete user
# ---------------------------------------------------------------------------


@app.route("/admin/users/<uid>/delete", methods=["POST"])
@admin_required
def admin_delete_user(uid):
    """Burahon ang account (Firebase Auth + Firestore profile)."""
    if uid == g.uid:  # Dili puwede burahon ang kaugalingong account dinhi.
        flash("You can't delete your own account here.", "warning")
        return redirect(url_for("admin_users"))

    profile = firebase_db.get_profile(uid)
    if profile is None:
        flash("That user doesn't exist.", "danger")
        return redirect(url_for("admin_users"))

    if profile.get("role") == "admin" and firebase_db.count_admins() <= 1:
        flash("The last admin can't be deleted.", "warning")  # Proteksyon sa katapusang admin.
        return redirect(url_for("admin_users"))

    try:
        try:
            firebase_db.delete_auth_user(uid)  # Burahon sa Authentication.
        except auth.UserNotFoundError:
            pass  # wala na sa Authentication, limpyohan na lang ang profile
        firebase_db.delete_profile(uid)  # Burahon ang profile sa Firestore.
    except GoogleAPICallError as error:
        flash(f"Firebase error: {error}", "danger")
        return redirect(url_for("admin_users"))

    flash(f"{profile.get('username', uid)}'s account has been deleted.", "success")
    return redirect(url_for("admin_users"))


# ---------------------------------------------------------------------------
# ROUTE: logout
# ---------------------------------------------------------------------------


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    try:
        firebase_db.revoke_sessions(g.uid)  # Revoke tanan session/refresh tokens.
    except Exception:  # ok lang bisan dili ma-revoke
        pass
    session.clear()  # Limpyohan ang session.
    flash("You've been logged out. Take care!", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# PAGPADAGAN SA APP
# Kini lang ang modagan kung direct nga gi-run ang file (dili kung gi-import).
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    app.run(debug=True, port=5000)  # debug=True = auto-reload ug detailed errors.
