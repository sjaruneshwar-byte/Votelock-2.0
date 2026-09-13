from flask import Blueprint, render_template, request, jsonify, session
from database import get_db, add_audit_log

qr_bp=Blueprint("qr",__name__,url_prefix="/qr")

@qr_bp.route("/scanner")
def scanner():
    if "voter_id" not in session and "admin_id" not in session: return __import__("flask").redirect(__import__("flask").url_for("auth.voter_login"))
    return render_template("voter_qr_scanner.html")

@qr_bp.route("/verify",methods=["POST"])
def verify_qr():
    data=request.get_json(silent=True) or {}; token=(data.get("qr_token") or "").strip()
    if not token: return jsonify(success=False,message="No QR token received."),400
    conn=get_db(); voter=conn.execute("SELECT voter_id,name,email,department,has_voted,image_path FROM voters WHERE qr_token=?",(token,)).fetchone(); conn.close()
    if not voter: return jsonify(success=False,message="Invalid QR code. Voter not found."),404
    if voter["has_voted"]: status="ALREADY_VOTED"
    else: status="ELIGIBLE"
    if "voter_id" in session and session["voter_id"]!=voter["voter_id"]:
        return jsonify(success=False,message="This QR code does not belong to the signed-in voter."),403
    session["qr_verified"] = True
    session["verified_voter_id"] = voter["voter_id"]
    add_audit_log("QR_VERIFIED",f"QR verified for voter {voter['voter_id']}.",voter["voter_id"])
    return jsonify(success=True,message="QR verified.",status=status,voter=dict(voter))
