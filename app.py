import os
import socket
import time

import psycopg
from flask import Flask, redirect, request
from markupsafe import escape

app = Flask(__name__)

DB_URL = (
    f"host={os.environ['DB_HOST']} dbname={os.environ['DB_NAME']} "
    f"user={os.environ['DB_USER']} password={os.environ['DB_PASSWORD']}"
)


def get_conn():
    for attempt in range(10):
        try:
            return psycopg.connect(DB_URL)
        except psycopg.OperationalError:
            print(f"Database not ready, retrying ({attempt + 1}/10)...", flush=True)
            time.sleep(2)
    raise RuntimeError("Could not connect to the database")


def init_db():
    with get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS assets (
                   id SERIAL PRIMARY KEY,
                   name TEXT NOT NULL,
                   type TEXT NOT NULL,
                   assigned_to TEXT,
                   added TIMESTAMP DEFAULT now()
               )"""
        )
    print("Database ready", flush=True)


STYLE = """
<style>
  body { font-family: Segoe UI, Arial, sans-serif; max-width: 850px; margin: 40px auto; padding: 0 16px; }
  table { border-collapse: collapse; width: 100%; margin-top: 20px; }
  th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
  th { background: #0b5394; color: white; }
  form.add input, form.add select { padding: 6px; margin-right: 6px; }
  .footer { margin-top: 30px; color: #888; font-size: 12px; }
</style>
"""


@app.route("/")
def index():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, type, assigned_to, added FROM assets ORDER BY id"
        ).fetchall()

    table_rows = "".join(
        f"<tr><td>{r[0]}</td><td>{escape(r[1])}</td><td>{escape(r[2])}</td>"
        f"<td>{escape(r[3] or '')}</td><td>{r[4]:%Y-%m-%d %H:%M}</td>"
        f"<td><form method='post' action='/delete/{r[0]}'><button>Delete</button></form></td></tr>"
        for r in rows
    )

    return f"""<!doctype html><html><head><title>IT Asset Register</title>{STYLE}</head><body>
<h1>IT Asset Register v1.1</h1>
<form class="add" method="post" action="/add">
  <input name="name" placeholder="Device name (e.g. LT-0042)" required>
  <select name="type"><option>Laptop</option><option>Desktop</option><option>Monitor</option><option>Phone</option><option>Other</option></select>
  <input name="assigned_to" placeholder="Assigned to">
  <button>Add asset</button>
</form>
<table><tr><th>ID</th><th>Name</th><th>Type</th><th>Assigned to</th><th>Added</th><th></th></tr>{table_rows}</table>
<p class="footer">Served by container {socket.gethostname()} | {len(rows)} assets</p>
</body></html>"""


@app.route("/add", methods=["POST"])
def add():
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO assets (name, type, assigned_to) VALUES (%s, %s, %s)",
            (request.form["name"], request.form["type"], request.form.get("assigned_to", "")),
        )
    return redirect("/")


@app.route("/delete/<int:asset_id>", methods=["POST"])
def delete(asset_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
    return redirect("/")


@app.route("/health")
def health():
    return "OK"


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
