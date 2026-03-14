"""
Football Championship Manager - Backend API
Uses only Python stdlib + Flask (already installed)
Run: python3 server.py
"""

import sqlite3
import hashlib
import hmac
import json
import base64
import time
import secrets
import os
from functools import wraps
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "championship.db")
JWT_SECRET = os.environ.get("JWT_SECRET", "football_secret_key_2024_xyz")

# ─── CORS (manual, no flask-cors needed) ─────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        from flask import Response
        r = Response()
        r.headers["Access-Control-Allow-Origin"] = "*"
        r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return r, 200

# ─── DATABASE ─────────────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            short_name TEXT NOT NULL,
            logo_color TEXT DEFAULT '#1a73e8',
            city TEXT,
            founded INTEGER,
            coach TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            away_team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            home_score INTEGER,
            away_score INTEGER,
            match_date TEXT NOT NULL,
            matchweek INTEGER DEFAULT 1,
            venue TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER UNIQUE NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            played INTEGER DEFAULT 0,
            won INTEGER DEFAULT 0,
            drawn INTEGER DEFAULT 0,
            lost INTEGER DEFAULT 0,
            goals_for INTEGER DEFAULT 0,
            goals_against INTEGER DEFAULT 0,
            goal_difference INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER REFERENCES matches(id) ON DELETE SET NULL,
            reporter_name TEXT DEFAULT 'Anonymous',
            telegram_user_id TEXT,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            admin_note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    db.commit()

    # Seed admin
    admin = db.execute("SELECT id FROM admins LIMIT 1").fetchone()
    if not admin:
        pw = _hash_password("admin123")
        db.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ("admin", pw))
        db.commit()

    # Seed demo teams + matches
    count = db.execute("SELECT COUNT(*) as c FROM teams").fetchone()["c"]
    if count == 0:
        _seed_demo(db)

    db.close()

def _hash_password(pw):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"

def _verify_password(pw, stored):
    try:
        salt, h = stored.split(":")
        check = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100000)
        return hmac.compare_digest(h, check.hex())
    except Exception:
        return False

def _seed_demo(db):
    teams = [
        ("Real Madrid", "RMA", "#b8860b", "Madrid", 1902, "Carlo Ancelotti"),
        ("Barcelona", "BAR", "#A50044", "Barcelona", 1899, "Xavi Hernández"),
        ("Atletico Madrid", "ATM", "#CB3524", "Madrid", 1903, "Diego Simeone"),
        ("Sevilla", "SEV", "#D10024", "Sevilla", 1890, "Quique Sanchez"),
        ("Valencia", "VAL", "#FF8000", "Valencia", 1919, "Ruben Baraja"),
        ("Villarreal", "VIL", "#c8a000", "Villarreal", 1923, "Marcelino"),
        ("Real Sociedad", "RSO", "#003DA5", "San Sebastián", 1909, "Imanol Alguacil"),
        ("Athletic Bilbao", "ATH", "#EE2523", "Bilbao", 1898, "Ernesto Valverde"),
    ]
    team_ids = []
    for t in teams:
        cur = db.execute(
            "INSERT INTO teams (name, short_name, logo_color, city, founded, coach) VALUES (?,?,?,?,?,?)", t
        )
        tid = cur.lastrowid
        db.execute("INSERT INTO standings (team_id) VALUES (?)", (tid,))
        team_ids.append(tid)
    db.commit()

    a, b, c, d, e, f, g2, h = team_ids
    matches = [
        (a, b, 2, 1, "2024-09-15", 1, "Santiago Bernabéu", "finished"),
        (c, d, 1, 1, "2024-09-16", 1, "Metropolitano",     "finished"),
        (e, f, 0, 2, "2024-09-17", 1, "Mestalla",          "finished"),
        (g2,h, 3, 0, "2024-09-18", 1, "Anoeta",            "finished"),
        (b, c, 2, 2, "2024-09-22", 2, "Camp Nou",          "finished"),
        (a, d, 4, 0, "2024-09-23", 2, "Santiago Bernabéu", "finished"),
        (f, g2,1, 0, "2024-09-24", 2, "La Cerámica",       "finished"),
        (h, e, 2, 1, "2024-09-25", 2, "San Mamés",         "finished"),
        (a, c, 3, 1, "2024-10-05", 3, "Santiago Bernabéu", "finished"),
        (b, e, 2, 0, "2024-10-06", 3, "Camp Nou",          "finished"),
        (d, h, 0, 1, "2024-10-07", 3, "Ramón Sánchez",     "finished"),
        (f, e, None, None, "2024-10-20", 4, "La Cerámica",        "scheduled"),
        (a, g2,None, None, "2024-10-21", 4, "Santiago Bernabéu",  "scheduled"),
        (c, h, None, None, "2024-10-22", 4, "Metropolitano",       "scheduled"),
    ]
    for m in matches:
        db.execute(
            "INSERT INTO matches (home_team_id,away_team_id,home_score,away_score,match_date,matchweek,venue,status) VALUES (?,?,?,?,?,?,?,?)",
            m
        )
    db.commit()
    _recalculate_standings(db)

def _recalculate_standings(db):
    db.execute("UPDATE standings SET played=0,won=0,drawn=0,lost=0,goals_for=0,goals_against=0,goal_difference=0,points=0")
    rows = db.execute(
        "SELECT * FROM matches WHERE status='finished' AND home_score IS NOT NULL AND away_score IS NOT NULL"
    ).fetchall()
    for row in rows:
        hs, as_ = row["home_score"], row["away_score"]
        hid, aid = row["home_team_id"], row["away_team_id"]
        if hs > as_:
            hw, hd, hl, hp = 1, 0, 0, 3
            aw, ad, al, ap = 0, 0, 1, 0
        elif hs == as_:
            hw, hd, hl, hp = 0, 1, 0, 1
            aw, ad, al, ap = 0, 1, 0, 1
        else:
            hw, hd, hl, hp = 0, 0, 1, 0
            aw, ad, al, ap = 1, 0, 0, 3
        db.execute("""UPDATE standings SET
            played=played+1, won=won+?, drawn=drawn+?, lost=lost+?,
            goals_for=goals_for+?, goals_against=goals_against+?,
            points=points+?
            WHERE team_id=?""", (hw, hd, hl, hs, as_, hp, hid))
        db.execute("""UPDATE standings SET
            played=played+1, won=won+?, drawn=drawn+?, lost=lost+?,
            goals_for=goals_for+?, goals_against=goals_against+?,
            points=points+?
            WHERE team_id=?""", (aw, ad, al, as_, hs, ap, aid))
    db.execute("UPDATE standings SET goal_difference = goals_for - goals_against")
    db.commit()

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)

# ─── JWT (manual, no PyJWT needed) ───────────────────────────────────────────
def _b64url_encode(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s):
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)

def create_token(payload):
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
    payload["exp"] = int(time.time()) + 86400
    body = _b64url_encode(json.dumps(payload))
    sig_input = f"{header}.{body}".encode()
    sig = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"

def verify_token(token):
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, body, sig = parts
        sig_input = f"{header}.{body}".encode()
        expected = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_decode(sig), expected):
            return None
        payload = json.loads(_b64url_decode(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "").strip()
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Unauthorized"}), 401
        g.admin = payload
        return f(*args, **kwargs)
    return decorated

# ─── ROUTES: AUTH ─────────────────────────────────────────────────────────────
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    db = get_db()
    admin = row_to_dict(db.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone())
    if not admin or not _verify_password(password, admin["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_token({"id": admin["id"], "username": admin["username"]})
    return jsonify({"token": token, "username": admin["username"]})

# ─── ROUTES: TEAMS ────────────────────────────────────────────────────────────
@app.route("/api/teams", methods=["GET"])
def get_teams():
    db = get_db()
    search = request.args.get("search", "")
    if search:
        rows = db.execute(
            "SELECT * FROM teams WHERE name LIKE ? OR city LIKE ? ORDER BY name",
            (f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM teams ORDER BY name").fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route("/api/teams/<int:tid>", methods=["GET"])
def get_team(tid):
    db = get_db()
    team = row_to_dict(db.execute("SELECT * FROM teams WHERE id=?", (tid,)).fetchone())
    if not team:
        return jsonify({"error": "Team not found"}), 404
    standing = row_to_dict(db.execute("SELECT * FROM standings WHERE team_id=?", (tid,)).fetchone())
    recent = db.execute("""
        SELECT m.*, ht.name as home_team_name, ht.short_name as home_short, ht.logo_color as home_color,
               at.name as away_team_name, at.short_name as away_short, at.logo_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id=ht.id
        JOIN teams at ON m.away_team_id=at.id
        WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status='finished'
        ORDER BY m.match_date DESC LIMIT 5
    """, (tid, tid)).fetchall()
    team["standing"] = standing
    team["recentMatches"] = [row_to_dict(r) for r in recent]
    return jsonify(team)

@app.route("/api/teams", methods=["POST"])
@require_auth
def create_team():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    short_name = data.get("short_name", "").strip()
    if not name or not short_name:
        return jsonify({"error": "name and short_name required"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO teams (name,short_name,logo_color,city,founded,coach) VALUES (?,?,?,?,?,?)",
            (name, short_name, data.get("logo_color","#1a73e8"), data.get("city"),
             data.get("founded"), data.get("coach"))
        )
        tid = cur.lastrowid
        db.execute("INSERT INTO standings (team_id) VALUES (?)", (tid,))
        db.commit()
        return jsonify({"id": tid, "message": "Team created"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Team name already exists"}), 409

@app.route("/api/teams/<int:tid>", methods=["PUT"])
@require_auth
def update_team(tid):
    data = request.get_json() or {}
    db = get_db()
    db.execute(
        "UPDATE teams SET name=?,short_name=?,logo_color=?,city=?,founded=?,coach=? WHERE id=?",
        (data.get("name"), data.get("short_name"), data.get("logo_color"),
         data.get("city"), data.get("founded"), data.get("coach"), tid)
    )
    db.commit()
    return jsonify({"message": "Team updated"})

@app.route("/api/teams/<int:tid>", methods=["DELETE"])
@require_auth
def delete_team(tid):
    db = get_db()
    db.execute("DELETE FROM teams WHERE id=?", (tid,))
    db.commit()
    return jsonify({"message": "Team deleted"})

# ─── ROUTES: MATCHES ──────────────────────────────────────────────────────────
@app.route("/api/matches", methods=["GET"])
def get_matches():
    db = get_db()
    status    = request.args.get("status")
    from_date = request.args.get("from")
    to_date   = request.args.get("to")
    matchweek = request.args.get("matchweek")
    page      = int(request.args.get("page", 1))
    limit     = int(request.args.get("limit", 20))

    where, params = [], []
    if status:     where.append("m.status=?");           params.append(status)
    if from_date:  where.append("m.match_date>=?");      params.append(from_date)
    if to_date:    where.append("m.match_date<=?");      params.append(to_date)
    if matchweek:  where.append("m.matchweek=?");        params.append(matchweek)
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.execute(f"""
        SELECT COUNT(*) as c FROM matches m
        JOIN teams ht ON m.home_team_id=ht.id
        JOIN teams at ON m.away_team_id=at.id {clause}
    """, params).fetchone()["c"]

    rows = db.execute(f"""
        SELECT m.*, ht.name as home_team_name, ht.short_name as home_short, ht.logo_color as home_color,
               at.name as away_team_name, at.short_name as away_short, at.logo_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id=ht.id
        JOIN teams at ON m.away_team_id=at.id
        {clause}
        ORDER BY m.match_date DESC, m.id DESC
        LIMIT ? OFFSET ?
    """, params + [limit, (page-1)*limit]).fetchall()

    return jsonify({
        "matches": [row_to_dict(r) for r in rows],
        "total": total, "page": page,
        "pages": max(1, -(-total // limit))
    })

@app.route("/api/matches/<int:mid>", methods=["GET"])
def get_match(mid):
    db = get_db()
    row = db.execute("""
        SELECT m.*, ht.name as home_team_name, ht.short_name as home_short, ht.logo_color as home_color,
               at.name as away_team_name, at.short_name as away_short, at.logo_color as away_color
        FROM matches m
        JOIN teams ht ON m.home_team_id=ht.id
        JOIN teams at ON m.away_team_id=at.id
        WHERE m.id=?
    """, (mid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(row_to_dict(row))

@app.route("/api/matches", methods=["POST"])
@require_auth
def create_match():
    data = request.get_json() or {}
    hid = data.get("home_team_id")
    aid = data.get("away_team_id")
    date = data.get("match_date")
    if not hid or not aid or not date:
        return jsonify({"error": "home_team_id, away_team_id, match_date required"}), 400
    if hid == aid:
        return jsonify({"error": "Teams must be different"}), 400
    hs = data.get("home_score")
    as_ = data.get("away_score")
    status = "finished" if (hs is not None and as_ is not None) else data.get("status","scheduled")
    db = get_db()
    cur = db.execute(
        "INSERT INTO matches (home_team_id,away_team_id,match_date,matchweek,venue,home_score,away_score,status) VALUES (?,?,?,?,?,?,?,?)",
        (hid, aid, date, data.get("matchweek",1), data.get("venue"), hs, as_, status)
    )
    db.commit()
    if status == "finished":
        _recalculate_standings(db)
    return jsonify({"id": cur.lastrowid, "message": "Match created"}), 201

@app.route("/api/matches/<int:mid>", methods=["PUT"])
@require_auth
def update_match(mid):
    data = request.get_json() or {}
    hs = data.get("home_score")
    as_ = data.get("away_score")
    status = "finished" if (hs is not None and as_ is not None) else data.get("status","scheduled")
    db = get_db()
    db.execute(
        "UPDATE matches SET home_team_id=?,away_team_id=?,match_date=?,matchweek=?,venue=?,home_score=?,away_score=?,status=? WHERE id=?",
        (data.get("home_team_id"), data.get("away_team_id"), data.get("match_date"),
         data.get("matchweek",1), data.get("venue"), hs, as_, status, mid)
    )
    db.commit()
    _recalculate_standings(db)
    return jsonify({"message": "Match updated"})

@app.route("/api/matches/<int:mid>", methods=["DELETE"])
@require_auth
def delete_match(mid):
    db = get_db()
    db.execute("DELETE FROM matches WHERE id=?", (mid,))
    db.commit()
    _recalculate_standings(db)
    return jsonify({"message": "Match deleted"})

# ─── ROUTES: STANDINGS ────────────────────────────────────────────────────────
@app.route("/api/standings", methods=["GET"])
def get_standings():
    db = get_db()
    rows = db.execute("""
        SELECT s.*, t.name, t.short_name, t.logo_color, t.city, t.coach
        FROM standings s JOIN teams t ON s.team_id=t.id
        ORDER BY s.points DESC, s.goal_difference DESC, s.goals_for DESC, t.name ASC
    """).fetchall()
    result = []
    for i, r in enumerate(rows):
        d = row_to_dict(r)
        d["position"] = i + 1
        result.append(d)
    return jsonify(result)

# ─── ROUTES: REPORTS ──────────────────────────────────────────────────────────
@app.route("/api/reports", methods=["POST"])
def submit_report():
    data = request.get_json() or {}
    msg = data.get("message","").strip()
    if not msg:
        return jsonify({"error": "Message required"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO reports (match_id,reporter_name,telegram_user_id,message) VALUES (?,?,?,?)",
        (data.get("match_id"), data.get("reporter_name","Anonymous"),
         data.get("telegram_user_id"), msg)
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, "message": "Report submitted"}), 201

@app.route("/api/reports", methods=["GET"])
@require_auth
def get_reports():
    db = get_db()
    status = request.args.get("status")
    page   = int(request.args.get("page", 1))
    limit  = int(request.args.get("limit", 20))
    where  = "WHERE r.status=?" if status else ""
    params = [status] if status else []
    total  = db.execute(f"SELECT COUNT(*) as c FROM reports r {where}", params).fetchone()["c"]
    rows   = db.execute(f"""
        SELECT r.*, m.match_date, m.home_score, m.away_score,
               ht.name as home_team_name, at.name as away_team_name
        FROM reports r
        LEFT JOIN matches m ON r.match_id=m.id
        LEFT JOIN teams ht ON m.home_team_id=ht.id
        LEFT JOIN teams at ON m.away_team_id=at.id
        {where} ORDER BY r.created_at DESC LIMIT ? OFFSET ?
    """, params + [limit, (page-1)*limit]).fetchall()
    return jsonify({
        "reports": [row_to_dict(r) for r in rows],
        "total": total, "page": page,
        "pages": max(1, -(-total // limit))
    })

@app.route("/api/reports/<int:rid>", methods=["PUT"])
@require_auth
def update_report(rid):
    data = request.get_json() or {}
    db = get_db()
    db.execute("UPDATE reports SET status=?,admin_note=? WHERE id=?",
               (data.get("status"), data.get("admin_note"), rid))
    db.commit()
    return jsonify({"message": "Report updated"})

# ─── ROUTES: STATS ────────────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def get_stats():
    db = get_db()
    return jsonify({
        "teams":          db.execute("SELECT COUNT(*) as c FROM teams").fetchone()["c"],
        "matches":        db.execute("SELECT COUNT(*) as c FROM matches").fetchone()["c"],
        "finished":       db.execute("SELECT COUNT(*) as c FROM matches WHERE status='finished'").fetchone()["c"],
        "scheduled":      db.execute("SELECT COUNT(*) as c FROM matches WHERE status='scheduled'").fetchone()["c"],
        "pendingReports": db.execute("SELECT COUNT(*) as c FROM reports WHERE status='pending'").fetchone()["c"],
        "topScorer":      row_to_dict(db.execute(
            "SELECT t.name, s.goals_for FROM standings s JOIN teams t ON s.team_id=t.id ORDER BY s.goals_for DESC LIMIT 1"
        ).fetchone()),
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def run_server():
    """
    Production WSGI server chain:
      1. waitress  — best pure-Python option (pip install waitress)
      2. gunicorn  — standard Linux choice  (pip install gunicorn)
      3. wsgiref   — Python stdlib fallback, single-threaded but warning-free
    Never uses Flask's built-in dev server in this path.
    """
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 3001))

    # ── 1. waitress ──────────────────────────────────────────────────────────
    try:
        from waitress import serve
        print(f"🚀  Football Championship API  →  http://{host}:{port}")
        print("    Server: waitress (production)")
        serve(app, host=host, port=port, threads=8)
        return
    except ImportError:
        pass

    # ── 2. gunicorn ──────────────────────────────────────────────────────────
    try:
        import gunicorn  # noqa: F401  (presence check only)
        import subprocess, sys
        print(f"🚀  Football Championship API  →  http://{host}:{port}")
        print("    Server: gunicorn (production)")
        subprocess.run([
            sys.executable, "-m", "gunicorn",
            "--bind", f"{host}:{port}",
            "--workers", "4",
            "--access-logfile", "-",
            "server:app",
        ])
        return
    except ImportError:
        pass

    # ── 3. wsgiref (stdlib) ──────────────────────────────────────────────────
    from wsgiref.simple_server import make_server, WSGIRequestHandler

    class QuietHandler(WSGIRequestHandler):
        """Suppress the per-request stdout noise from wsgiref."""
        def log_message(self, fmt, *args):
            pass  # uncomment below to re-enable request logging
            # print(f"  {self.address_string()} - {fmt % args}")

    print(f"🚀  Football Championship API  →  http://{host}:{port}")
    print("    Server: wsgiref (stdlib) — suitable for low-traffic / local use")
    print("    Tip:  pip install waitress  for a multi-threaded production server")

    httpd = make_server(host, port, app, handler_class=QuietHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋  Server stopped.")
        httpd.server_close()


if __name__ == "__main__":
    print("⚽  Initialising database...")
    init_db()
    print("✅  Database ready")
    run_server()