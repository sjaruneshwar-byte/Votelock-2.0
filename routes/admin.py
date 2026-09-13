from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from database import get_dashboard_stats, get_recent_logs, get_all_voters, get_all_candidates

admin_bp=Blueprint("admin",__name__,url_prefix="/admin")

def admin_required(): return "admin_id" in session

@admin_bp.before_request
def protect():
    if not admin_required(): return redirect(url_for("auth.login", next=request.path))

@admin_bp.route("/")
def home(): return redirect(url_for("admin.dashboard"))

@admin_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", stats=get_dashboard_stats(), logs=get_recent_logs(12), admin_name=session.get("admin_name","Administrator"), voters=get_all_voters()[:6], candidates=get_all_candidates()[:6])

@admin_bp.route("/logs")
def logs(): return render_template("logs.html", logs=get_recent_logs(100))
