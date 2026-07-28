from flask import Flask, request, jsonify
import sqlite3
import secrets
from datetime import datetime

app = Flask(__name__)
DB = "licenses.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS licenses (
        key TEXT PRIMARY KEY,
        active INTEGER DEFAULT 1,
        created_at TEXT,
        hwid TEXT
    )""")
    conn.commit()
    conn.close()

ADMIN_TOKEN = "ESDTXRCYFTGYVHUIJOMRDCTVFGYHBIUNJ"

@app.route("/admin/reset_hwid", methods=["POST"])
def reset_hwid():
    if request.headers.get("Authorization") != ADMIN_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    key = request.json.get("key")
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE licenses SET hwid='' WHERE key=?", (key,))
    conn.commit()
    conn.close()
    return jsonify({"status": "hwid_reset"})
    
# ── TYMCZASOWY endpoint diagnostyczny — usunąć po znalezieniu problemu ──
@app.route("/debug")
def debug():
    return jsonify({
        "received_header": request.headers.get("Authorization"),
        "expected": ADMIN_TOKEN,
        "match": request.headers.get("Authorization") == ADMIN_TOKEN
    })

@app.route("/admin/create", methods=["POST"])
def create_license():
    if request.headers.get("Authorization") != ADMIN_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    key = secrets.token_hex(16)
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO licenses (key, active, created_at) VALUES (?, 1, ?)",
                 (key, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"key": key})

@app.route("/admin/revoke", methods=["POST"])
def revoke_license():
    if request.headers.get("Authorization") != ADMIN_TOKEN:
        return jsonify({"error": "unauthorized"}), 401
    key = request.json.get("key")
    conn = sqlite3.connect(DB)
    conn.execute("UPDATE licenses SET active=0 WHERE key=?", (key,))
    conn.commit()
    conn.close()
    return jsonify({"status": "revoked"})

@app.route("/check", methods=["GET"])
def check_license():
    key = request.args.get("key")
    hwid = request.args.get("hwid", "")
    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT active, hwid FROM licenses WHERE key=?", (key,)).fetchone()
    if not row:
        return jsonify({"valid": False, "reason": "not_found"})
    active, saved_hwid = row
    if not active:
        return jsonify({"valid": False, "reason": "revoked"})
    if saved_hwid == "":
        conn.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid, key))
        conn.commit()
    elif saved_hwid != hwid:
        conn.close()
        return jsonify({"valid": False, "reason": "hwid_mismatch"})
    conn.close()
    return jsonify({"valid": True})

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
