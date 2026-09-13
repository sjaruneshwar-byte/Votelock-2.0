from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db,get_all_candidates,get_candidate,delete_candidate,add_audit_log

candidates_bp=Blueprint("candidates",__name__,url_prefix="/candidates")
def guard():
    if "admin_id" not in session: return redirect(url_for("auth.login"))

@candidates_bp.route("/")
def list_candidates():
    r=guard()
    if r: return r
    return render_template("candidates/list.html",candidates=get_all_candidates())

@candidates_bp.route("/add",methods=["GET","POST"])
def add_candidate():
    r=guard()
    if r: return r
    if request.method=="POST":
        cid=request.form.get("candidate_id","").strip().upper(); name=request.form.get("name","").strip(); symbol=request.form.get("symbol","").strip(); party=request.form.get("party","").strip(); desc=request.form.get("description","").strip()
        if not cid or not name: flash("Candidate ID and name are required.","error"); return redirect(url_for("candidates.add_candidate"))
        conn=get_db()
        try:
            conn.execute("INSERT INTO candidates(candidate_id,name,symbol,party,description) VALUES(?,?,?,?,?)",(cid,name,symbol,party,desc)); conn.commit(); add_audit_log("CANDIDATE_ADDED",f"Candidate {cid} was added."); flash("Candidate added successfully.","success")
        except Exception as exc: conn.rollback(); flash("Candidate ID already exists." if "UNIQUE" in str(exc).upper() else f"Unable to add candidate: {exc}","error")
        finally: conn.close()
        return redirect(url_for("candidates.list_candidates"))
    return render_template("candidates/add.html")

@candidates_bp.route("/<candidate_id>/edit",methods=["GET","POST"])
def edit_candidate(candidate_id):
    r=guard()
    if r: return r
    candidate=get_candidate(candidate_id)
    if not candidate: flash("Candidate not found.","error"); return redirect(url_for("candidates.list_candidates"))
    if request.method=="POST":
        name=request.form.get("name","").strip(); symbol=request.form.get("symbol","").strip(); party=request.form.get("party","").strip(); desc=request.form.get("description","").strip(); status=request.form.get("status","Active")
        if not name: flash("Candidate name is required.","error"); return redirect(url_for("candidates.edit_candidate",candidate_id=candidate_id))
        conn=get_db(); conn.execute("UPDATE candidates SET name=?,symbol=?,party=?,description=?,status=? WHERE candidate_id=?",(name,symbol,party,desc,status,candidate_id)); conn.commit(); conn.close(); add_audit_log("CANDIDATE_UPDATED",f"Candidate {candidate_id} was updated."); flash("Candidate updated successfully.","success"); return redirect(url_for("candidates.list_candidates"))
    return render_template("edit_candidate.html",candidate=candidate)

@candidates_bp.route("/delete/<candidate_id>",methods=["POST"])
def remove_candidate(candidate_id):
    r=guard()
    if r: return r
    ok,msg=delete_candidate(candidate_id); flash(msg,"success" if ok else "error")
    if ok: add_audit_log("CANDIDATE_DELETED",f"Candidate {candidate_id} was removed.")
    return redirect(url_for("candidates.list_candidates"))

@candidates_bp.route("/<candidate_id>")
def candidate_details(candidate_id):
    r=guard()
    if r: return r
    candidate=get_candidate(candidate_id)
    if not candidate: flash("Candidate not found.","error"); return redirect(url_for("candidates.list_candidates"))
    return render_template("candidates/details.html",candidate=candidate)
