import os
from pathlib import Path
from flask import Flask, redirect, url_for, send_from_directory
from dotenv import load_dotenv

from database import init_db

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["ELECTION_NAME"] = os.getenv("ELECTION_NAME", "VoteLock Demo Election")
app.config["UPLOAD_FOLDER"] = str(BASE_DIR / "static" / "uploads")
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

init_db()

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.voters import voters_bp
from routes.candidates import candidates_bp
from routes.qr import qr_bp
from routes.verification import verification_bp
from routes.voting import voting_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(voters_bp)
app.register_blueprint(candidates_bp)
app.register_blueprint(qr_bp)
app.register_blueprint(verification_bp)
app.register_blueprint(voting_bp)

@app.context_processor
def inject_globals():
    return {"election_name": app.config["ELECTION_NAME"]}

@app.route("/")
def index():
    if "admin_id" in __import__("flask").session:
        return redirect(url_for("admin.dashboard"))
    if "voter_id" in __import__("flask").session:
        return redirect(url_for("voting.voter_home"))
    return redirect(url_for("auth.login"))

@app.route("/health")
def health():
    return {"status": "ok", "application": "VoteLock", "version": "Review-1"}

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # Admin-only access to captured voter images.
    from flask import session, abort
    if "admin_id" not in session:
        abort(403)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    print("=" * 60)
    print("VoteLock Smart Electronic Voting System - Review 1")
    print("Login     : http://127.0.0.1:5000/login")
    print("Register  : http://127.0.0.1:5000/register")
    print("Dashboard : http://127.0.0.1:5000/admin/dashboard")
    print("Voter app : http://127.0.0.1:5000/voter/login")
    print("QR scan   : http://127.0.0.1:5000/qr/scanner")
    print("=" * 60)
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=True)
