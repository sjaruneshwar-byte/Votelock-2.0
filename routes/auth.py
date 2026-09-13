import os
import random
import hashlib
import smtplib
import time
import sqlite3

from email.message import EmailMessage

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import (
    get_db,
    add_audit_log,
    get_voter_by_username
)


# ============================================================
# BLUEPRINT
# ============================================================

auth_bp = Blueprint("auth", __name__)


# ============================================================
# SEND OTP EMAIL
# ============================================================

def send_otp_email(receiver_email, otp):
    """
    Send administrator registration OTP using Gmail SMTP.

    Required .env variables:

        SMTP_EMAIL=your_email@gmail.com
        SMTP_PASSWORD=your_gmail_app_password
        SMTP_SERVER=smtp.gmail.com
        SMTP_PORT=587

    Returns:
        True  -> email sent successfully
        False -> email could not be sent
    """

    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    smtp_server = os.getenv(
        "SMTP_SERVER",
        "smtp.gmail.com"
    )

    try:
        smtp_port = int(
            os.getenv(
                "SMTP_PORT",
                "587"
            )
        )
    except ValueError:
        smtp_port = 587


    # --------------------------------------------------------
    # CHECK SMTP CONFIGURATION
    # --------------------------------------------------------

    if not sender_email or not sender_password:

        print()
        print("=" * 60)
        print("EMAIL CONFIGURATION ERROR")
        print("=" * 60)
        print("SMTP_EMAIL or SMTP_PASSWORD is missing.")
        print()
        print("Check your .env file.")
        print("=" * 60)
        print()

        return False


    # Gmail App Passwords may contain spaces.
    # Remove spaces before authentication.

    sender_password = sender_password.replace(" ", "")


    # --------------------------------------------------------
    # CREATE EMAIL
    # --------------------------------------------------------

    message = EmailMessage()

    message["Subject"] = (
        "VoteLock - Administrator Email Verification"
    )

    message["From"] = sender_email

    message["To"] = receiver_email

    message.set_content(
        f"""
Hello,

Welcome to VoteLock Smart Electronic Voting System.

Your administrator registration OTP is:

    {otp}

This OTP is valid for 10 minutes.

Please do not share this OTP with anyone.

If you did not request administrator registration,
please ignore this email.

Regards,

VoteLock
Smart Electronic Voting System
"""
    )


    # --------------------------------------------------------
    # SEND EMAIL
    # --------------------------------------------------------

    try:

        print()
        print("=" * 60)
        print("CONNECTING TO GMAIL SMTP")
        print("=" * 60)

        with smtplib.SMTP(
            smtp_server,
            smtp_port,
            timeout=30
        ) as server:

            server.ehlo()

            print("Starting TLS encryption...")

            server.starttls()

            server.ehlo()

            print("Logging into Gmail...")

            server.login(
                sender_email,
                sender_password
            )

            print("Sending OTP...")

            server.send_message(message)


        print("=" * 60)
        print("OTP EMAIL SENT SUCCESSFULLY")
        print("=" * 60)
        print(f"Recipient : {receiver_email}")
        print("=" * 60)
        print()

        return True


    # --------------------------------------------------------
    # GMAIL AUTHENTICATION ERROR
    # --------------------------------------------------------

    except smtplib.SMTPAuthenticationError as e:

        print()
        print("=" * 60)
        print("GMAIL AUTHENTICATION FAILED")
        print("=" * 60)
        print()
        print("Check:")
        print()
        print("1. SMTP_EMAIL is correct.")
        print("2. SMTP_PASSWORD is a Gmail App Password.")
        print("3. 2-Step Verification is enabled.")
        print("4. The App Password has not been revoked.")
        print()
        print("SMTP ERROR:")
        print(e)
        print("=" * 60)
        print()

        return False


    # --------------------------------------------------------
    # OTHER SMTP ERROR
    # --------------------------------------------------------

    except smtplib.SMTPException as e:

        print()
        print("=" * 60)
        print("SMTP ERROR")
        print("=" * 60)
        print(e)
        print("=" * 60)
        print()

        return False


    # --------------------------------------------------------
    # GENERAL ERROR
    # --------------------------------------------------------

    except Exception as e:

        print()
        print("=" * 60)
        print("EMAIL ERROR")
        print("=" * 60)
        print(type(e).__name__)
        print(e)
        print("=" * 60)
        print()

        return False


# ============================================================
# ADMIN LOGIN
# ============================================================

@auth_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    # --------------------------------------------------------
    # ALREADY LOGGED IN
    # --------------------------------------------------------

    if "admin_id" in session:

        return redirect(
            url_for("admin.dashboard")
        )


    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not email or not password:

            flash(
                "Enter both email and password.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )


        # ----------------------------------------------------
        # FIND ADMIN
        # ----------------------------------------------------

        conn = get_db()

        admin = conn.execute(
            """
            SELECT *
            FROM admins
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()


        # ----------------------------------------------------
        # INVALID LOGIN
        # ----------------------------------------------------

        if not admin:

            flash(
                "Invalid administrator credentials.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )


        # ----------------------------------------------------
        # CHECK PASSWORD
        # ----------------------------------------------------

        if not check_password_hash(
            admin["password_hash"],
            password
        ):

            flash(
                "Invalid administrator credentials.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )


        # ----------------------------------------------------
        # CHECK EMAIL VERIFICATION
        # ----------------------------------------------------

        if not admin["is_verified"]:

            flash(
                "Verify your email before logging in.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )


        # ----------------------------------------------------
        # CREATE ADMIN SESSION
        # ----------------------------------------------------

        session.clear()

        session["admin_id"] = admin["id"]

        session["admin_name"] = admin["name"]

        session["admin_email"] = admin["email"]


        # ----------------------------------------------------
        # AUDIT LOG
        # ----------------------------------------------------

        try:

            add_audit_log(
                "ADMIN_LOGIN",
                f"Administrator {admin['email']} logged in."
            )

        except Exception as e:

            print(
                "Audit log warning:",
                e
            )


        # ----------------------------------------------------
        # DASHBOARD
        # ----------------------------------------------------

        return redirect(
            url_for("admin.dashboard")
        )


    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render_template(
        "login.html"
    )


# ============================================================
# ADMIN REGISTRATION
# ============================================================

@auth_bp.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm = request.form.get(
            "confirm_password",
            ""
        )


        # ----------------------------------------------------
        # REQUIRED FIELDS
        # ----------------------------------------------------

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )


        # ----------------------------------------------------
        # PASSWORD MATCH
        # ----------------------------------------------------

        if password != confirm:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )


        # ----------------------------------------------------
        # PASSWORD LENGTH
        # ----------------------------------------------------

        if len(password) < 8:

            flash(
                "Use at least 8 characters for the password.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )


        # ----------------------------------------------------
        # CHECK EXISTING ADMIN
        # ----------------------------------------------------

        conn = get_db()

        exists = conn.execute(
            """
            SELECT id
            FROM admins
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        conn.close()


        if exists:

            flash(
                "An administrator with this email already exists.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )


        # ----------------------------------------------------
        # GENERATE OTP
        # ----------------------------------------------------

        otp = f"{random.SystemRandom().randint(100000, 999999)}"

        otp_hash = hashlib.sha256(
            otp.encode()
        ).hexdigest()


        # ----------------------------------------------------
        # SAVE REGISTRATION DATA IN SESSION
        # ----------------------------------------------------

        session["registration_name"] = name

        session["registration_email"] = email

        session["registration_password"] = (
            generate_password_hash(password)
        )

        session["registration_otp"] = otp_hash

        # 600 seconds = 10 minutes

        session["otp_expiry"] = (
            time.time() + 600
        )


        # ----------------------------------------------------
        # SEND OTP
        # ----------------------------------------------------

        email_sent = send_otp_email(
            email,
            otp
        )


        if not email_sent:

            # Remove registration OTP information
            # because the user did not receive it.

            session.pop(
                "registration_otp",
                None
            )

            session.pop(
                "otp_expiry",
                None
            )

            flash(
                "Could not send OTP. Check SMTP settings.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        flash(
            "OTP sent successfully. Check your email.",
            "success"
        )

        return redirect(
            url_for("auth.verify_otp")
        )


    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render_template(
        "register.html"
    )


# ============================================================
# VERIFY ADMIN OTP
# ============================================================

@auth_bp.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    # --------------------------------------------------------
    # CHECK REGISTRATION SESSION
    # --------------------------------------------------------

    if "registration_email" not in session:

        flash(
            "Please register first.",
            "error"
        )

        return redirect(
            url_for("auth.register")
        )


    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        otp = request.form.get(
            "otp",
            ""
        ).strip()


        # ----------------------------------------------------
        # OTP FORMAT
        # ----------------------------------------------------

        if not otp.isdigit() or len(otp) != 6:

            flash(
                "Enter the valid 6-digit OTP.",
                "error"
            )

            return redirect(
                url_for("auth.verify_otp")
            )


        # ----------------------------------------------------
        # CHECK EXPIRY
        # ----------------------------------------------------

        expiry = session.get(
            "otp_expiry",
            0
        )

        if time.time() > expiry:

            flash(
                "OTP expired. Please register again.",
                "error"
            )

            return redirect(
                url_for("auth.register")
            )


        # ----------------------------------------------------
        # HASH ENTERED OTP
        # ----------------------------------------------------

        entered_hash = hashlib.sha256(
            otp.encode()
        ).hexdigest()


        # ----------------------------------------------------
        # COMPARE OTP
        # ----------------------------------------------------

        if entered_hash != session.get(
            "registration_otp"
        ):

            flash(
                "Invalid OTP. Please try again.",
                "error"
            )

            return redirect(
                url_for("auth.verify_otp")
            )


        # ----------------------------------------------------
        # INSERT ADMIN
        # ----------------------------------------------------

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO admins
                (
                    name,
                    email,
                    password_hash,
                    is_verified
                )
                VALUES (?, ?, ?, 1)
                """,
                (
                    session["registration_name"],
                    session["registration_email"],
                    session["registration_password"]
                )
            )

            conn.commit()


        except sqlite3.IntegrityError:

            conn.rollback()

            flash(
                "Administrator already exists.",
                "error"
            )

            return redirect(
                url_for("auth.login")
            )


        finally:

            conn.close()


        # ----------------------------------------------------
        # AUDIT LOG
        # ----------------------------------------------------

        try:

            add_audit_log(
                "ADMIN_REGISTERED",
                (
                    "Administrator "
                    f"{session['registration_email']} "
                    "registered successfully."
                )
            )

        except Exception as e:

            print(
                "Audit log warning:",
                e
            )


        # ----------------------------------------------------
        # CLEAR OTP SESSION
        # ----------------------------------------------------

        session.pop(
            "registration_name",
            None
        )

        session.pop(
            "registration_email",
            None
        )

        session.pop(
            "registration_password",
            None
        )

        session.pop(
            "registration_otp",
            None
        )

        session.pop(
            "otp_expiry",
            None
        )


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        flash(
            "Registration successful. You can now sign in.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )


    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render_template(
        "verify_otp.html",
        email=session.get(
            "registration_email"
        )
    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@auth_bp.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("auth.login")
    )


# ============================================================
# VOTER LOGIN
# ============================================================

@auth_bp.route(
    "/voter/login",
    methods=["GET", "POST"]
)
def voter_login():

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip().upper()

        password = request.form.get(
            "password",
            ""
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not username or not password:

            flash(
                "Enter your voter username and password.",
                "error"
            )

            return redirect(
                url_for("auth.voter_login")
            )


        # ----------------------------------------------------
        # FIND VOTER
        # ----------------------------------------------------

        voter = get_voter_by_username(
            username
        )


        # ----------------------------------------------------
        # INVALID CREDENTIALS
        # ----------------------------------------------------

        if (
            not voter
            or not voter["password_hash"]
            or not check_password_hash(
                voter["password_hash"],
                password
            )
        ):

            flash(
                "Invalid voter credentials.",
                "error"
            )

            return redirect(
                url_for("auth.voter_login")
            )


        # ----------------------------------------------------
        # PREVENT ALREADY VOTED VOTER FROM STARTING AGAIN
        # ----------------------------------------------------

        if voter["status"] == "VOTED":

            flash(
                "You have already completed voting.",
                "error"
            )

            return redirect(
                url_for("auth.voter_login")
            )


        # ----------------------------------------------------
        # CREATE VOTER SESSION
        # ----------------------------------------------------

        session.clear()

        session["qr_verified"] = False

        session["face_captured"] = False

        session["voter_id"] = voter["voter_id"]

        session["voter_name"] = voter["name"]

        session["voter_username"] = voter["username"]


        # ----------------------------------------------------
        # VOTER HOME
        # ----------------------------------------------------

        return redirect(
            url_for("voting.voter_home")
        )


    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render_template(
        "voter_login.html"
    )


# ============================================================
# VOTER LOGOUT
# ============================================================

@auth_bp.route(
    "/voter/logout"
)
def voter_logout():

    session.clear()

    return redirect(
        url_for("auth.voter_login")
    )