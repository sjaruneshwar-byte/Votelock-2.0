import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from database import get_db, get_all_candidates, get_voter, add_audit_log

voting_bp=Blueprint("voting",__name__)

def voter_guard(): return "voter_id" in session

@voting_bp.route("/voter")
def voter_home():
    if not voter_guard(): return redirect(url_for("auth.voter_login"))
    voter=get_voter(session["voter_id"])
    return render_template("voter_home.html",voter=voter)

@voting_bp.route("/voting")
def voting_page():
    if not voter_guard(): return redirect(url_for("auth.voter_login"))
    if not session.get("qr_verified") or session.get("verified_voter_id") != session.get("voter_id"):
        return redirect(url_for("voting.voter_home"))
    if not session.get("face_captured"):
        return redirect(url_for("verification.camera"))
    voter=get_voter(session["voter_id"])
    if not voter: session.clear(); return redirect(url_for("auth.voter_login"))
    if voter["has_voted"]: return render_template("vote_complete.html",voter=voter)
    return render_template("voting.html",voter=voter,candidates=get_all_candidates())

@voting_bp.route("/api/cast",methods=["POST"])
def cast_vote():
    if not voter_guard(): return jsonify(success=False,message="Voter login required."),401
    if not session.get("qr_verified") or session.get("verified_voter_id") != session.get("voter_id"):
        return jsonify(success=False,message="Complete QR verification first."),403
    if not session.get("face_captured"):
        return jsonify(success=False,message="Complete camera verification first."),403
    voter_id=session["voter_id"]; data=request.get_json(silent=True) or {}; cid=(data.get("candidate_id") or "").strip()
    conn=get_db()
    try:
        voter=conn.execute("SELECT * FROM voters WHERE voter_id=?",(voter_id,)).fetchone()
        candidate=conn.execute("SELECT * FROM candidates WHERE candidate_id=? AND status='Active'",(cid,)).fetchone()
        if not voter: return jsonify(success=False,message="Voter not found."),404
        if voter["has_voted"]: return jsonify(success=False,message="Vote already recorded for this voter."),409
        if not candidate: return jsonify(success=False,message="Candidate is not available."),400
        conn.execute("INSERT INTO votes(candidate_id) VALUES(?)",(candidate["id"],))
        conn.execute("UPDATE voters SET has_voted=1 WHERE voter_id=?",(voter_id,))
        conn.commit()
    except Exception as exc:
        conn.rollback(); return jsonify(success=False,message=f"Vote could not be recorded: {exc}"),500
    finally: conn.close()
    add_audit_log("VOTE_CAST",f"Vote recorded successfully for voter {voter_id}.",voter_id)
    printer_status="disabled"
    if os.getenv("THERMAL_PRINTER_ENABLED","false").lower()=="true":
        try:
            from hardware.thermal_printer import print_vvpat
            printer_status=print_vvpat(candidate["name"],candidate["symbol"] or "",os.getenv("ELECTION_NAME","VoteLock Demo Election"))
        except Exception as exc: printer_status=f"printer-error: {exc}"
    return jsonify(success=True,message="Vote recorded successfully.",candidate_name=candidate["name"],printer_status=printer_status)
