import os, uuid, json, hashlib, secrets, re, random, string
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import bcrypt
from flask import Flask, request, jsonify, render_template, g, redirect, url_for, session
from flask_cors import CORS
import jwt as pyjwt

# ─── SETUP ───────────────────────────────────────
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "findit-secret-2024-change-in-prod")
CORS(app, supports_credentials=True)

JWT_SECRET    = os.getenv("JWT_SECRET", "findit-jwt-secret-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_H = 168   # 7 days
DATA_FILE     = Path("data.json")
OTP_EXPIRY_M  = 2   # OTP valid for 2 minutes

# ─── DATABASE (JSON file) ─────────────────────────
def load_db():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "users": [], "sessions": [], "items": [], "matches": [],
        "messages": [], "notifications": [], "otps": [],
        "categories": [
            {"id": "electronics", "name": "Electronics",     "icon": "fa-laptop"},
            {"id": "documents",   "name": "Documents & IDs", "icon": "fa-id-card"},
            {"id": "accessories", "name": "Accessories",     "icon": "fa-key"},
            {"id": "clothing",    "name": "Clothing",        "icon": "fa-tshirt"},
            {"id": "jewelry",     "name": "Jewelry",         "icon": "fa-gem"},
            {"id": "other",       "name": "Other",           "icon": "fa-box"},
        ],
        "seed_done": False
    }

def save_db(db):
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=2, default=str)

def get_db():
    if "db" not in g:
        g.db = load_db()
        if not g.db.get("seed_done"):
            _seed(g.db)
    return g.db

def _seed(db):
    for u in [
        {"name": "Aarav Sharma", "email": "aarav@example.com", "password": "password123", "phone": "+91 98765 43210"},
        {"name": "Priya Nair",   "email": "priya@example.com", "password": "password123", "phone": "+91 87654 32109"},
    ]:
        if not any(x["email"] == u["email"] for x in db["users"]):
            db["users"].append({
                "id": str(uuid.uuid4()), "full_name": u["name"], "email": u["email"],
                "phone": u["phone"], "otp_verified": True,
                "password_hash": bcrypt.hashpw(u["password"].encode(), bcrypt.gensalt(10)).decode(),
                "kyc_status": "verified", "trust_score": 88.0,
                "items_returned": 3, "items_found": 5, "is_banned": False,
                "created_at": _now(),
            })
    uid1 = db["users"][0]["id"]
    uid2 = db["users"][1]["id"] if len(db["users"]) > 1 else uid1
    if not db["items"]:
        db["items"] = [
            {"id": str(uuid.uuid4()), "user_id": uid1, "report_type": "lost",
             "title": "iPhone 13 Pro", "category": "electronics",
             "description": "Blue iPhone 13 Pro, clear case, scratch on bottom right. IMEI: 354321098765432.",
             "unique_identifiers": "IMEI: 354321098765432",
             "location_label": "Central Park, New Delhi", "event_time": "2024-01-15",
             "status": "active", "is_high_value": True, "reward": "₹5,000", "created_at": "2024-01-15T10:30:00"},
            {"id": str(uuid.uuid4()), "user_id": uid2, "report_type": "found",
             "title": "Brown Leather Wallet", "category": "accessories",
             "description": "Brown leather wallet found near counter. Contains cards but no cash.",
             "unique_identifiers": "", "location_label": "Starbucks, MG Road, Bengaluru",
             "event_time": "2024-01-16", "status": "active", "is_high_value": False,
             "reward": "", "created_at": "2024-01-16T14:20:00"},
            {"id": str(uuid.uuid4()), "user_id": uid1, "report_type": "lost",
             "title": "Dell XPS 13 Laptop", "category": "electronics",
             "description": "Silver Dell XPS 13, black sleeve, university sticker on back. Serial: DX13-987654.",
             "unique_identifiers": "Serial: DX13-987654",
             "location_label": "IIT Delhi Library", "event_time": "2024-01-14",
             "status": "active", "is_high_value": True, "reward": "₹10,000", "created_at": "2024-01-14T09:15:00"},
            {"id": str(uuid.uuid4()), "user_id": uid2, "report_type": "found",
             "title": "Car Keys with Red Keychain", "category": "accessories",
             "description": "Toyota key fob with distinctive red keychain. Found near parking section B.",
             "unique_identifiers": "", "location_label": "Ambience Mall, Gurgaon",
             "event_time": "2024-01-17", "status": "active", "is_high_value": False,
             "reward": "", "created_at": "2024-01-17T16:45:00"},
            {"id": str(uuid.uuid4()), "user_id": uid1, "report_type": "lost",
             "title": "Gold Necklace with Pendant", "category": "jewelry",
             "description": "18k gold necklace, small diamond pendant. Bought from Tanishq. Receipt no. 2023-456.",
             "unique_identifiers": "Tanishq receipt no. 2023-456",
             "location_label": "Riverside Restaurant, Mumbai", "event_time": "2024-01-13",
             "status": "active", "is_high_value": True, "reward": "₹15,000", "created_at": "2024-01-13T20:00:00"},
            {"id": str(uuid.uuid4()), "user_id": uid2, "report_type": "found",
             "title": "Aadhaar Card", "category": "documents",
             "description": "Aadhaar card found at metro station. Last 4 digits: xxxx 5678.",
             "unique_identifiers": "", "location_label": "Rajiv Chowk Metro, Delhi",
             "event_time": "2024-01-18", "status": "active", "is_high_value": False,
             "reward": "", "created_at": "2024-01-18T08:30:00"},
        ]
    db["seed_done"] = True
    save_db(db)

# ─── HELPERS ─────────────────────────────────────
def ok(data=None, status=200):
    return jsonify({"success": True, "data": data}), status

def fail(msg, status=400):
    return jsonify({"success": False, "error": msg}), status

def _now():
    return datetime.now(timezone.utc).isoformat()

def valid_email(e):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", e))

def valid_phone(p):
    return bool(re.match(r"^\+?[\d\s\-]{7,15}$", p))

def _gen_otp():
    return "".join(random.choices(string.digits, k=6))

def _send_otp_email(email, otp, name=""):
    """Simulate email sending — in production connect SMTP/SendGrid."""
    print(f"\n{'='*40}")
    print(f"  📧 OTP EMAIL to {email}")
    print(f"  Name: {name or 'User'}")
    print(f"  OTP Code: {otp}")
    print(f"  Valid for {OTP_EXPIRY_M} minutes")
    print(f"{'='*40}\n")
    return True

def _send_otp_sms(phone, otp):
    """Simulate SMS — in production connect Twilio/MSG91."""
    print(f"\n{'='*40}")
    print(f"  📱 OTP SMS to {phone}")
    print(f"  OTP Code: {otp}")
    print(f"  Valid for {OTP_EXPIRY_M} minutes")
    print(f"{'='*40}\n")
    return True

def make_jwt(user_id):
    jti = str(uuid.uuid4())
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_H)
    token = pyjwt.encode({"sub": user_id, "jti": jti, "exp": exp},
                         JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, jti, exp.isoformat()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "").strip() if auth.startswith("Bearer ") else None
        if not token:
            return fail("No token provided", 401)
        try:
            payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except pyjwt.ExpiredSignatureError:
            return fail("Token expired", 401)
        except pyjwt.InvalidTokenError:
            return fail("Invalid token", 401)
        db = get_db()
        sess = next((s for s in db["sessions"] if s["jti"] == payload["jti"] and not s.get("revoked")), None)
        if not sess: return fail("Session expired", 401)
        user = next((u for u in db["users"] if u["id"] == payload["sub"]), None)
        if not user or user.get("is_banned"): return fail("Account suspended", 403)
        g.user_id = user["id"]
        g.user = user
        g.jti = payload["jti"]
        return f(*args, **kwargs)
    return decorated

def serialize_item(item, db):
    d = dict(item)
    cat = next((c for c in db["categories"] if c["id"] == d.get("category")), None)
    d["category_name"] = cat["name"] if cat else d.get("category", "")
    user = next((u for u in db["users"] if u["id"] == d.get("user_id")), None)
    d["reporter_name"] = user["full_name"] if user else "Anonymous"
    return d

def run_matching(new_item, db):
    opp = "found" if new_item["report_type"] == "lost" else "lost"
    for item in db["items"]:
        if item["report_type"] != opp or item["status"] != "active" or item["id"] == new_item["id"]:
            continue
        exists = any(
            (m["lost_id"] == new_item["id"] or m["found_id"] == new_item["id"]) and
            (m["lost_id"] == item["id"] or m["found_id"] == item["id"])
            for m in db["matches"]
        )
        if exists: continue
        cat_score = 0.4 if item["category"] == new_item["category"] else 0.0
        w1 = set(new_item["title"].lower().split())
        w2 = set(item["title"].lower().split())
        text_score = (len(w1 & w2) / max(len(w1 | w2), 1)) * 0.5
        l1 = (new_item.get("location_label") or "").lower()
        l2 = (item.get("location_label") or "").lower()
        loc_score = 0.1 if l1 and l2 and (l1 in l2 or l2 in l1) else 0.0
        score = round(cat_score + text_score + loc_score, 4)
        if score < 0.2: continue
        signals = []
        if cat_score > 0: signals.append("category_match")
        if text_score > 0: signals.append("text_similarity")
        if loc_score > 0: signals.append("location_match")
        lost_id  = new_item["id"] if new_item["report_type"] == "lost"  else item["id"]
        found_id = new_item["id"] if new_item["report_type"] == "found" else item["id"]
        db["matches"].append({
            "id": str(uuid.uuid4()), "lost_id": lost_id, "found_id": found_id,
            "confidence_score": score, "match_signals": signals,
            "match_status": "notified" if score >= 0.5 else "pending_review",
            "matched_at": _now(),
        })
        lost_i  = next((i for i in db["items"] if i["id"] == lost_id), None)
        found_i = next((i for i in db["items"] if i["id"] == found_id), None)
        if lost_i:
            db["notifications"].append({"id": str(uuid.uuid4()), "user_id": lost_i["user_id"],
                "type": "match.found", "is_read": False, "created_at": _now(),
                "title": "Potential match found!",
                "body": f"A found item may match your lost '{lost_i['title']}'"})
        if found_i:
            db["notifications"].append({"id": str(uuid.uuid4()), "user_id": found_i["user_id"],
                "type": "match.found", "is_read": False, "created_at": _now(),
                "title": "Match found for your report!",
                "body": "Someone's lost item matches what you found."})

# ═══════════════════════════════════════════════════
# PAGE ROUTES  (Flask renders each template)
# ═══════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/browse")
def browse():
    return render_template("browse.html")

@app.route("/report-lost")
def report_lost():
    return render_template("report_lost.html")

@app.route("/report-found")
def report_found():
    return render_template("report_found.html")

@app.route("/matches")
def matches_page():
    return render_template("matches.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/profile")
def profile_page():
    return render_template("profile.html")

@app.get("/health")
def health():
    return jsonify({"status": "ok", "ts": _now()})

# ═══════════════════════════════════════════════════
# OTP AUTH ROUTES
# ═══════════════════════════════════════════════════

@app.post("/api/auth/send-otp")
def send_otp():
    """Send OTP via email or phone for login/register."""
    b = request.get_json(force=True) or {}
    contact = (b.get("contact") or "").strip()   # email or phone
    purpose = b.get("purpose", "login")           # login | register

    if not contact:
        return fail("Email or phone number required")

    is_email = valid_email(contact)
    is_phone = valid_phone(contact) and not is_email

    if not is_email and not is_phone:
        return fail("Please enter a valid email or phone number")

    db  = get_db()
    otp = _gen_otp()
    exp = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_M)).isoformat()

    # Remove old OTPs for this contact
    db["otps"] = [o for o in db.get("otps", []) if o["contact"] != contact]
    db["otps"].append({
        "id":      str(uuid.uuid4()),
        "contact": contact,
        "otp":     otp,
        "purpose": purpose,
        "expires_at": exp,
        "used":    False,
    })
    save_db(db)

    # Send OTP
    if is_email:
        user = next((u for u in db["users"] if u["email"] == contact), None)
        _send_otp_email(contact, otp, user["full_name"] if user else "")
        masked = contact[:2] + "***@" + contact.split("@")[1] if "@" in contact else contact
    else:
        _send_otp_sms(contact, otp)
        masked = contact[:3] + "****" + contact[-3:]

    return ok({"message": f"OTP sent to {masked}", "masked": masked, "via": "email" if is_email else "sms"})


@app.post("/api/auth/verify-otp")
def verify_otp():
    """Verify OTP and log in (or complete registration step)."""
    b = request.get_json(force=True) or {}
    contact  = (b.get("contact") or "").strip()
    otp_code = (b.get("otp") or "").strip()
    full_name= (b.get("full_name") or "").strip()   # needed for register

    if not contact or not otp_code:
        return fail("Contact and OTP are required")

    db = get_db()
    now = datetime.now(timezone.utc)
    rec = next((o for o in db.get("otps", [])
                if o["contact"] == contact and not o["used"]), None)

    if not rec:
        return fail("No OTP found. Please request a new one.")
    if rec["otp"] != otp_code:
        return fail("Incorrect OTP. Please try again.")
    if datetime.fromisoformat(rec["expires_at"]) < now:
        return fail(f"OTP expired. Please request a new one.")

    # Mark OTP used
    rec["used"] = True
    save_db(db)

    is_email = valid_email(contact)
    # Find or create user
    user = next((u for u in db["users"] if u["email"] == contact or u.get("phone") == contact), None)

    if not user:
        # Auto-register on first OTP login
        if not full_name:
            # Ask frontend to provide a name
            return ok({"needs_name": True, "contact": contact, "message": "OTP verified. Please provide your name to complete registration."})
        user = {
            "id": str(uuid.uuid4()),
            "full_name": full_name,
            "email": contact if is_email else "",
            "phone": contact if not is_email else "",
            "password_hash": "",
            "otp_verified": True,
            "kyc_status": "otp_verified",
            "trust_score": 50.0,
            "items_returned": 0, "items_found": 0,
            "is_banned": False, "created_at": _now(),
        }
        db["users"].append(user)
        save_db(db)

    token, jti, exp = make_jwt(user["id"])
    db["sessions"].append({"user_id": user["id"], "jti": jti, "expires_at": exp,
                            "revoked": False, "created_at": _now()})
    save_db(db)

    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return ok({"token": token, "user": safe, "is_new": not bool(user.get("otp_verified"))})


@app.post("/api/auth/register")
def register():
    b = request.get_json(force=True) or {}
    full_name = (b.get("full_name") or "").strip()
    email     = (b.get("email") or "").strip().lower()
    password  = b.get("password") or ""
    phone     = (b.get("phone") or "").strip()

    if not full_name: return fail("Full name is required")
    if not email or not valid_email(email): return fail("Valid email is required")
    if len(password) < 8: return fail("Password must be at least 8 characters")

    db = get_db()
    if any(u["email"] == email for u in db["users"]):
        return fail("Email already registered", 409)

    user = {
        "id": str(uuid.uuid4()), "full_name": full_name, "email": email,
        "phone": phone, "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode(),
        "otp_verified": False, "kyc_status": "pending", "trust_score": 50.0,
        "items_returned": 0, "items_found": 0, "is_banned": False, "created_at": _now(),
    }
    db["users"].append(user)
    save_db(db)
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return ok(safe, 201)


@app.post("/api/auth/login")
def login():
    b = request.get_json(force=True) or {}
    email    = (b.get("email") or "").strip().lower()
    password = b.get("password") or ""
    if not email or not password: return fail("Email and password are required")
    db = get_db()
    user = next((u for u in db["users"] if u["email"] == email), None)
    if not user or not user.get("password_hash"):
        return fail("Invalid email or password", 401)
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return fail("Invalid email or password", 401)
    if user.get("is_banned"): return fail("Account suspended", 403)
    token, jti, exp = make_jwt(user["id"])
    db["sessions"].append({"user_id": user["id"], "jti": jti, "expires_at": exp,
                            "revoked": False, "created_at": _now()})
    save_db(db)
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return ok({"token": token, "user": safe})


@app.post("/api/auth/logout")
@require_auth
def logout():
    db = get_db()
    for s in db["sessions"]:
        if s["jti"] == g.jti:
            s["revoked"] = True
    save_db(db)
    return ok({"message": "Logged out"})

# ═══════════════════════════════════════════════════
# USER ROUTES
# ═══════════════════════════════════════════════════

@app.get("/api/users/me")
@require_auth
def me():
    safe = {k: v for k, v in g.user.items() if k != "password_hash"}
    return ok(safe)

@app.patch("/api/users/me")
@require_auth
def update_me():
    b = request.get_json(force=True) or {}
    db = get_db()
    for u in db["users"]:
        if u["id"] == g.user_id:
            if b.get("full_name"): u["full_name"] = b["full_name"].strip()
            if b.get("phone"):     u["phone"]     = b["phone"].strip()
            save_db(db)
            return ok({k: v for k, v in u.items() if k != "password_hash"})
    return fail("User not found", 404)

# ═══════════════════════════════════════════════════
# CATEGORIES
# ═══════════════════════════════════════════════════

@app.get("/api/categories")
def categories():
    return ok(get_db()["categories"])



@app.post("/api/reports")
@require_auth
def create_report():
    b = request.get_json(force=True) or {}
    rtype = b.get("report_type", "")
    title = (b.get("title") or "").strip()
    desc  = (b.get("description") or "").strip()
    cat   = b.get("category") or ""
    if rtype not in ("lost","found"): return fail("report_type must be 'lost' or 'found'")
    if not title: return fail("Title is required")
    if not desc:  return fail("Description is required")
    if not cat:   return fail("Category is required")
    db = get_db()
    item = {
        "id": str(uuid.uuid4()), "user_id": g.user_id, "report_type": rtype,
        "title": title, "category": cat, "description": desc,
        "unique_identifiers": b.get("unique_identifiers") or "",
        "location_label": b.get("location_label") or b.get("location") or "",
        "event_time": b.get("event_time") or b.get("date") or "",
        "status": "active", "is_high_value": bool(b.get("is_high_value", False)),
        "reward": b.get("reward") or "",
        "contact_email": b.get("contact_email") or g.user.get("email", ""),
        "contact_phone": b.get("contact_phone") or g.user.get("phone", ""),
        "created_at": _now(),
    }
    db["items"].append(item)
    run_matching(item, db)
    save_db(db)
    return ok(serialize_item(item, db), 201)

@app.get("/api/reports")
@require_auth
def list_my_reports():
    tf = request.args.get("type","")
    sf = request.args.get("status","")
    db = get_db()
    items = [i for i in db["items"] if i["user_id"] == g.user_id]
    if tf: items = [i for i in items if i["report_type"] == tf]
    if sf: items = [i for i in items if i["status"] == sf]
    return ok([serialize_item(i, db) for i in sorted(items, key=lambda x: x["created_at"], reverse=True)])

@app.get("/api/reports/all")
def all_reports():
    tf = request.args.get("type","")
    cf = request.args.get("category","")
    q  = (request.args.get("q") or "").strip().lower()
    db = get_db()
    items = [i for i in db["items"] if i["status"] == "active"]
    if tf: items = [i for i in items if i["report_type"] == tf]
    if cf: items = [i for i in items if i["category"] == cf]
    if q:  items = [i for i in items if q in i["title"].lower()
                    or q in (i.get("location_label") or "").lower()
                    or q in i["description"].lower()]
    return ok([serialize_item(i, db) for i in sorted(items, key=lambda x: x["created_at"], reverse=True)])

@app.get("/api/reports/<item_id>")
def get_report(item_id):
    db = get_db()
    item = next((i for i in db["items"] if i["id"] == item_id), None)
    if not item: return fail("Item not found", 404)
    return ok(serialize_item(item, db))

@app.patch("/api/reports/<item_id>/status")
@require_auth
def update_report_status(item_id):
    b = request.get_json(force=True) or {}
    st = b.get("status")
    if st not in ("active","returned","removed"): return fail("Invalid status")
    db = get_db()
    for item in db["items"]:
        if item["id"] == item_id and item["user_id"] == g.user_id:
            item["status"] = st
            save_db(db)
            return ok({"id": item_id, "status": st})
    return fail("Item not found", 404)

# ═══════════════════════════════════════════════════
# MATCHES
# ═══════════════════════════════════════════════════

@app.get("/api/matches")
@require_auth
def list_matches():
    db = get_db()
    my_ids = {i["id"] for i in db["items"] if i["user_id"] == g.user_id}
    result = []
    for m in sorted([m for m in db["matches"] if m["lost_id"] in my_ids or m["found_id"] in my_ids],
                    key=lambda x: x["matched_at"], reverse=True):
        lost  = next((i for i in db["items"] if i["id"] == m["lost_id"]), {})
        found = next((i for i in db["items"] if i["id"] == m["found_id"]), {})
        result.append({"id": m["id"], "confidence_score": m["confidence_score"],
                       "match_status": m["match_status"], "match_signals": m["match_signals"],
                       "matched_at": m["matched_at"], "lost_title": lost.get("title","—"),
                       "found_title": found.get("title","—"),
                       "lost_report_id": m["lost_id"], "found_report_id": m["found_id"],
                       "owner_id": lost.get("user_id",""), "finder_id": found.get("user_id","")})
    return ok(result)

@app.post("/api/matches/<match_id>/verify")
@require_auth
def verify_match(match_id):
    b = request.get_json(force=True) or {}
    answer = (b.get("answer") or "").strip().lower()
    if not answer: return fail("Answer is required")
    db = get_db()
    match = next((m for m in db["matches"] if m["id"] == match_id), None)
    if not match: return fail("Match not found", 404)
    lost = next((i for i in db["items"] if i["id"] == match["lost_id"]), None)
    if not lost: return fail("Item not found", 404)
    secret = (lost.get("unique_identifiers") or lost.get("title") or "").strip().lower()
    if not secret: return fail("No verification secret set")
    if answer == secret or answer in secret:
        match["match_status"] = "verified"
        save_db(db)
        return ok({"verified": True, "message": "Verification passed! You can now chat securely."})
    return fail("Incorrect answer. Please try again.", 400)

# ═══════════════════════════════════════════════════
# CHAT
# ═══════════════════════════════════════════════════

@app.post("/api/chat/sessions")
@require_auth
def open_chat():
    b = request.get_json(force=True) or {}
    match_id = b.get("match_id")
    if not match_id: return fail("match_id required")
    db = get_db()
    match = next((m for m in db["matches"] if m["id"] == match_id and m["match_status"] == "verified"), None)
    if not match: return fail("Match not found or not verified", 404)
    lost  = next((i for i in db["items"] if i["id"] == match["lost_id"]),  {})
    found = next((i for i in db["items"] if i["id"] == match["found_id"]), {})
    if g.user_id not in (lost.get("user_id"), found.get("user_id")):
        return fail("Not a participant", 403)
    sess_key = f"chat_{match_id}"
    return ok({"id": sess_key, "match_id": match_id,
               "owner_alias":  "Owner#"  + str(1000 + abs(hash(match["lost_id"]))  % 9000),
               "finder_alias": "Finder#" + str(1000 + abs(hash(match["found_id"])) % 9000),
               "status": "active", "created_at": _now()})

@app.get("/api/chat/sessions")
@require_auth
def list_chat_sessions():
    db = get_db()
    my_ids = {i["id"] for i in db["items"] if i["user_id"] == g.user_id}
    sessions = []
    for m in db["matches"]:
        if m["match_status"] != "verified": continue
        if m["lost_id"] not in my_ids and m["found_id"] not in my_ids: continue
        lost = next((i for i in db["items"] if i["id"] == m["lost_id"]), {})
        sessions.append({"id": f"chat_{m['id']}", "match_id": m["id"],
                         "item_title": lost.get("title","Match"),
                         "owner_alias":  "Owner#"  + str(1000 + abs(hash(m["lost_id"]))  % 9000),
                         "finder_alias": "Finder#" + str(1000 + abs(hash(m["found_id"])) % 9000),
                         "status": "active", "created_at": m["matched_at"]})
    return ok(sessions)

@app.get("/api/chat/sessions/<session_id>/messages")
@require_auth
def get_messages(session_id):
    db = get_db()
    msgs = sorted([m for m in db["messages"] if m.get("session_id") == session_id], key=lambda x: x["sent_at"])
    result = []
    for m in msgs:
        user = next((u for u in db["users"] if u["id"] == m["sender_id"]), {})
        result.append({"id": m["id"], "sender_id": m["sender_id"],
                       "sender_name": user.get("full_name","Unknown"),
                       "content": m["content"], "sent_at": m["sent_at"]})
    return ok(result)

@app.post("/api/chat/sessions/<session_id>/messages")
@require_auth
def send_message(session_id):
    b = request.get_json(force=True) or {}
    content = (b.get("content") or "").strip()
    if not content: return fail("Message content required")
    if len(content) > 2000: return fail("Message too long")
    db = get_db()
    msg = {"id": str(uuid.uuid4()), "session_id": session_id,
           "sender_id": g.user_id, "content": content, "sent_at": _now()}
    db["messages"].append(msg)
    save_db(db)
    return ok({"id": msg["id"], "sender_id": msg["sender_id"], "sent_at": msg["sent_at"]}, 201)

# ═══════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════

@app.get("/api/notifications")
@require_auth
def get_notifications():
    db = get_db()
    notifs = sorted([n for n in db["notifications"] if n["user_id"] == g.user_id],
                    key=lambda x: x["created_at"], reverse=True)[:50]
    return ok(notifs)

@app.patch("/api/notifications/<notif_id>/read")
@require_auth
def mark_read(notif_id):
    db = get_db()
    for n in db["notifications"]:
        if n["id"] == notif_id and n["user_id"] == g.user_id:
            n["is_read"] = True
    save_db(db)
    return ok({"read": True})

@app.post("/api/notifications/read-all")
@require_auth
def mark_all_read():
    db = get_db()
    for n in db["notifications"]:
        if n["user_id"] == g.user_id: n["is_read"] = True
    save_db(db)
    return ok({"read": True})

# ═══════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════

@app.get("/api/stats")
def stats():
    db = get_db()
    items = db["items"]
    return ok({"total_items": len(items),
                "recovered": len([i for i in items if i["status"] == "returned"]),
                "active_users": len(db["users"])})

# ─── RUN ─────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n{'='*52}")
    print(f"  🔍 FindIt running → http://localhost:{port}")
    print(f"  📧 Demo: aarav@example.com / password123")
    print(f"  📱 OTP is printed to console (no SMTP needed)")
    print(f"{'='*52}\n")
    app.run(debug=True, host="0.0.0.0", port=port)
