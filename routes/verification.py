import base64, binascii, os, uuid
from flask import Blueprint, request, jsonify, session, current_app
from database import get_voter, add_audit_log, get_db

verification_bp=Blueprint("verification",__name__,url_prefix="/verification")

def auth_voter(voter_id): return "voter_id" in session and session.get("voter_id")==voter_id

@verification_bp.route("/camera")
def camera():
    from flask import render_template, redirect, url_for
    if "voter_id" not in session: return redirect(url_for("auth.voter_login"))
    if not session.get("qr_verified") or session.get("verified_voter_id") != session.get("voter_id"):
        return redirect(url_for("voting.voter_home"))
    return render_template("voter_verification.html")

@verification_bp.route("/capture",methods=["POST"])
def capture():
    if "voter_id" not in session: return jsonify(success=False,message="Voter login required."),401
    if not session.get("qr_verified") or session.get("verified_voter_id") != session.get("voter_id"):
        return jsonify(success=False,message="Complete QR verification first."),403
    data=request.get_json(silent=True) or {}; voter_id=session["voter_id"]; image=data.get("image","")
    if not image.startswith("data:image/"): return jsonify(success=False,message="Invalid image data."),400
    try:
        header,payload=image.split(",",1); raw=base64.b64decode(payload,validate=True)
    except (ValueError,binascii.Error): return jsonify(success=False,message="Could not decode captured image."),400
    if len(raw)>4*1024*1024: return jsonify(success=False,message="Image is too large."),413
    voter=get_voter(voter_id)
    if not voter: return jsonify(success=False,message="Voter not found."),404
    filename=f"{voter_id}_{uuid.uuid4().hex}.jpg"; path=os.path.join(current_app.config["UPLOAD_FOLDER"],filename)
    with open(path,"wb") as f: f.write(raw)
    conn=get_db(); conn.execute("UPDATE voters SET image_path=? WHERE voter_id=?",(filename,voter_id)); conn.commit(); conn.close()
    session["face_captured"] = True
    add_audit_log("FACE_CAPTURED",f"Verification image captured for voter {voter_id}.",voter_id)
    return jsonify(success=True,message="Face image captured successfully.",image_url=f"/uploads/{filename}")
