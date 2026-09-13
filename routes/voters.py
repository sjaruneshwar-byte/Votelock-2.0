import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash
from database import get_db,get_all_voters,get_voter,delete_voter,add_audit_log

voters_bp=Blueprint("voters",__name__)
def admin_required(): return "admin_id" in session

def guard():
    if not admin_required(): return redirect(url_for("auth.login"))

@voters_bp.route("/voters")
def list_voters():
    r=guard()
    if r: return r
    search=request.args.get("search","").strip().lower(); voters=get_all_voters()
    if search: voters=[v for v in voters if search in (v["voter_id"] or "").lower() or search in (v["name"] or "").lower() or search in (v["department"] or "").lower()]
    return render_template("voters.html",voters=voters,search=search)

@voters_bp.route("/voters/add",methods=["GET","POST"])
def add_voter():
    r=guard()
    if r: return r
    if request.method=="POST":
        voter_id=request.form.get("voter_id","").strip().upper(); name=request.form.get("name","").strip(); email=request.form.get("email","").strip(); department=request.form.get("department","").strip()
        if not voter_id or not name: flash("Voter ID and name are required.","error"); return redirect(url_for("voters.add_voter"))
        username="VOTER_"+voter_id; temp=secrets.token_urlsafe(7); qr_token=secrets.token_urlsafe(24)
        conn=get_db()
        try:
            conn.execute("INSERT INTO voters(voter_id,name,email,department,username,password_hash,qr_token) VALUES(?,?,?,?,?,?,?)",(voter_id,name,email,department,username,generate_password_hash(temp),qr_token)); conn.commit()
            add_audit_log("VOTER_ADDED",f"Voter {voter_id} was registered.",voter_id)
            session["generated_credentials"]={"voter_id":voter_id,"username":username,"password":temp}
            return redirect(url_for("voters.credentials"))
        except Exception as exc:
            conn.rollback(); flash("Voter ID or username already exists." if "UNIQUE" in str(exc).upper() else f"Unable to add voter: {exc}","error")
        finally: conn.close()
    return render_template("add_voter.html")

@voters_bp.route("/voters/credentials")
def credentials():
    r=guard()
    if r: return r
    data=session.pop("generated_credentials",None)
    if not data: flash("No newly generated credentials are available.","error"); return redirect(url_for("voters.list_voters"))
    return render_template("voter_credentials.html",credentials=data)

@voters_bp.route("/voters/qr/<voter_id>")
def view_qr(voter_id):
    r=guard()
    if r: return r
    voter=get_voter(voter_id)
    if not voter: flash("Voter not found.","error"); return redirect(url_for("voters.list_voters"))
    return render_template("voter_qr.html",voter=voter)

@voters_bp.route("/voters/edit/<voter_id>",methods=["GET","POST"])
def edit_voter(voter_id):
    r=guard()
    if r: return r
    voter=get_voter(voter_id)
    if not voter: flash("Voter not found.","error"); return redirect(url_for("voters.list_voters"))
    if request.method=="POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip(); department=request.form.get("department","").strip()
        if not name: flash("Name is required.","error"); return redirect(url_for("voters.edit_voter",voter_id=voter_id))
        conn=get_db()
        conn.execute("UPDATE voters SET name=?,email=?,department=? WHERE voter_id=?",(name,email,department,voter_id))
        conn.commit()
        conn.close()
        add_audit_log("VOTER_UPDATED",f"Voter {voter_id} was updated.",voter_id); flash("Voter updated successfully.","success"); return redirect(url_for("voters.list_voters"))
    return render_template("edit_voter.html",voter=voter)

@voters_bp.route("/voters/delete/<voter_id>",methods=["POST"])
def remove_voter(voter_id):
    r=guard()
    if r: return r
    ok,msg=delete_voter(voter_id); flash(msg,"success" if ok else "error")
    if ok: add_audit_log("VOTER_DELETED",f"Voter {voter_id} was deleted.",voter_id)
    return redirect(url_for("voters.list_voters"))
