import json
import os
import smtplib
import sqlite3
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "giftcards.db"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_FILE = BASE_DIR / "templates" / "index.html"

PRODUCTS = [
    {"id": "netflix", "name": "Netflix Premium", "price": 25, "currency": "USD", "description": "Streaming sans limite, 4K et multi-écrans.", "image": "https://images.unsplash.com/photo-1585951237318-9ea5e175b891?auto=format&fit=crop&w=800&q=80"},
    {"id": "playstation", "name": "PlayStation Store", "price": 50, "currency": "USD", "description": "Recharge ton wallet PSN et débloque tes jeux favoris.", "image": "https://images.unsplash.com/photo-1493711662062-fa541adb3fc8?auto=format&fit=crop&w=800&q=80"},
    {"id": "amazon", "name": "Amazon Gift Card", "price": 100, "currency": "USD", "description": "Shopping international livré selon ton besoin.", "image": "https://images.unsplash.com/photo-1523293836414-f04e712e1d9f?auto=format&fit=crop&w=800&q=80"},
    {"id": "itunes", "name": "Apple / iTunes", "price": 30, "currency": "USD", "description": "Apps, musique, iCloud et services Apple.", "image": "https://images.unsplash.com/photo-1581291519195-ef11498d1cf5?auto=format&fit=crop&w=800&q=80"},
]

PAYMENT_METHODS = ["M-Pesa", "Orange Money", "Airtel Money", "PayPal", "Carte de crédit"]


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gift_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                is_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                used_at TEXT,
                buyer_email TEXT,
                order_reference TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_reference TEXT NOT NULL UNIQUE,
                buyer_name TEXT NOT NULL,
                buyer_email TEXT NOT NULL,
                product_id TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                gift_code TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        existing = conn.execute("SELECT COUNT(*) AS c FROM gift_codes").fetchone()["c"]
        if existing == 0:
            now = datetime.utcnow().isoformat()
            rows = []
            for product in PRODUCTS:
                for i in range(1, 8):
                    rows.append((product["id"], f"{product['id'].upper()}-{i:04d}-KIN", now))
            conn.executemany("INSERT INTO gift_codes (product_id, code, created_at) VALUES (?, ?, ?)", rows)
        conn.commit()


def send_gift_code_email(recipient, buyer_name, product_name, code, payment_method):
    sender = os.getenv("MAIL_SENDER", "no-reply@kin-cards.com")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    content = (
        f"Salut {buyer_name},\n\n"
        f"Merci pour ton achat sur KinCards.\n\n"
        f"Produit: {product_name}\n"
        f"Code cadeau: {code}\n"
        f"Méthode de paiement: {payment_method}\n\n"
        "Note: la livraison peut prendre jusqu'à 30 minutes maximum.\n"
    )
    msg = EmailMessage()
    msg["Subject"] = f"Ton code {product_name} est prêt"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(content)

    if smtp_host and smtp_user and smtp_password:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        with open(BASE_DIR / "sent_emails.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.utcnow().isoformat()} ---\n{msg.as_string()}\n")


def json_response(start_response, status, payload):
    body = json.dumps(payload).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


def serve_file(start_response, path, content_type):
    if not path.exists():
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not Found"]
    data = path.read_bytes()
    start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(data)))])
    return [data]


def products_with_stock():
    result = []
    with get_db_connection() as conn:
        for product in PRODUCTS:
            stock = conn.execute("SELECT COUNT(*) AS c FROM gift_codes WHERE product_id = ? AND is_used = 0", (product["id"],)).fetchone()["c"]
            result.append({**product, "stock": stock})
    return result


def process_checkout(payload):
    buyer_name = (payload.get("buyer_name") or "").strip()
    buyer_email = (payload.get("buyer_email") or "").strip().lower()
    product_id = (payload.get("product_id") or "").strip()
    payment_method = (payload.get("payment_method") or "").strip()

    if not all([buyer_name, buyer_email, product_id, payment_method]):
        return 400, {"error": "Merci de remplir tous les champs."}

    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return 404, {"error": "Produit introuvable."}
    if payment_method not in PAYMENT_METHODS:
        return 400, {"error": "Méthode de paiement non supportée."}

    order_reference = f"KIN-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-3]}"
    with get_db_connection() as conn:
        code = conn.execute("SELECT id, code FROM gift_codes WHERE product_id = ? AND is_used = 0 ORDER BY id LIMIT 1", (product_id,)).fetchone()
        if not code:
            return 409, {"error": "Stock temporairement indisponible pour cette carte."}
        conn.execute("UPDATE gift_codes SET is_used = 1, used_at = ?, buyer_email = ?, order_reference = ? WHERE id = ?", (datetime.utcnow().isoformat(), buyer_email, order_reference, code["id"]))
        conn.execute(
            "INSERT INTO orders (order_reference, buyer_name, buyer_email, product_id, payment_method, amount, status, gift_code, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (order_reference, buyer_name, buyer_email, product_id, payment_method, product["price"], "paid_confirmed", code["code"], datetime.utcnow().isoformat()),
        )
        conn.commit()

    send_gift_code_email(buyer_email, buyer_name, product["name"], code["code"], payment_method)
    return 200, {"message": "Paiement confirmé. Le code cadeau a été envoyé par email.", "order_reference": order_reference, "delivery_notice": "Ton code peut arriver immédiatement ou dans un délai maximal de 30 minutes."}


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")

    if method == "GET" and path == "/":
        return serve_file(start_response, TEMPLATE_FILE, "text/html; charset=utf-8")
    if method == "GET" and path == "/api/products":
        return json_response(start_response, "200 OK", products_with_stock())
    if method == "GET" and path == "/api/config":
        return json_response(start_response, "200 OK", {"payment_methods": PAYMENT_METHODS})
    if path.startswith("/static/") and method == "GET":
        name = path.replace("/static/", "", 1)
        safe = (STATIC_DIR / name).resolve()
        if STATIC_DIR.resolve() not in safe.parents and safe != STATIC_DIR.resolve():
            start_response("403 Forbidden", [("Content-Type", "text/plain")])
            return [b"Forbidden"]
        content_type = "text/plain; charset=utf-8"
        if name.endswith(".css"):
            content_type = "text/css; charset=utf-8"
        elif name.endswith(".js"):
            content_type = "application/javascript; charset=utf-8"
        return serve_file(start_response, safe, content_type)

    if method == "POST" and path == "/api/checkout":
        size = int(environ.get("CONTENT_LENGTH") or 0)
        raw = environ["wsgi.input"].read(size) if size > 0 else b"{}"
        ctype = environ.get("CONTENT_TYPE", "")
        try:
            if "application/json" in ctype:
                payload = json.loads(raw.decode("utf-8") or "{}")
            else:
                payload = {k: v[0] for k, v in parse_qs(raw.decode("utf-8")).items()}
        except json.JSONDecodeError:
            return json_response(start_response, "400 Bad Request", {"error": "Payload invalide."})

        code, response = process_checkout(payload)
        status = "200 OK" if code == 200 else f"{code} Error"
        return json_response(start_response, status, response)

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not Found"]


init_db()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    with make_server("0.0.0.0", port, application) as server:
        print(f"KinCards running on http://0.0.0.0:{port}")
        server.serve_forever()
