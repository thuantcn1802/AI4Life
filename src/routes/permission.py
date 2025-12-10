# routes/permission.py
from functools import wraps
from flask import session, redirect, url_for, abort
from firebase_connect import db, verify_id_token

def get_user_profile_from_session():
    id_token = session.get("idToken")
    if not id_token:
        return None
    decoded = verify_id_token(id_token)
    if not decoded:
        return None
    uid = decoded.get("uid")
    if not uid:
        return None
    doc = db.collection("users").document(uid).get()
    return {"uid": uid, **(doc.to_dict() or {})} if doc.exists else None

def require_role(allowed_roles):
    if isinstance(allowed_roles, str):
        allowed = [allowed_roles]
    else:
        allowed = list(allowed_roles)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            profile = get_user_profile_from_session()
            if not profile:
                return redirect(url_for("auth.login"))
            role = profile.get("role")
            if role not in allowed:
                return abort(403)
            # if it's a doctor, ensure verified_by_admin True
            if role == "doctor" and not profile.get("verified_by_admin", False):
                return "Tài khoản bác sĩ chưa được xác minh bởi admin.", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
