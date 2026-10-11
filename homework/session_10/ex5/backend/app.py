import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pg8000.native

# Đọc cấu hình từ biến môi trường (do docker compose truyền vào)
DB_HOST = os.environ.get("DB_HOST", "database")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "appdb")
DB_USER = os.environ.get("DB_USER", "appuser")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
PORT = int(os.environ.get("PORT", "8080"))


def connect():
    # Mở một kết nối mới tới PostgreSQL
    return pg8000.native.Connection(
        user=DB_USER, password=DB_PASSWORD,
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
    )


def wait_for_db():
    # Thử kết nối tối đa 30 lần, cách nhau 1 giây
    for i in range(1, 31):
        try:
            conn = connect()
            conn.close()
            return True
        except Exception as e:
            print(f"Dang cho database ... ({i}/30) {e}", flush=True)
            time.sleep(1)
    return False


def init_db():
    # Tạo bảng notes nếu chưa tồn tại
    conn = connect()
    conn.run(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id SERIAL PRIMARY KEY, "
        "content TEXT NOT NULL, "
        "created_at TIMESTAMPTZ DEFAULT now())"
    )
    conn.close()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        # Trả JSON về cho client
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Ghi log mỗi request ra stdout để xem bằng docker compose logs
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self):
        if self.path == "/health":
            try:
                conn = connect()
                conn.run("SELECT 1")
                conn.close()
                db = "connected"
            except Exception as e:
                db = f"error: {e}"
            self._send(200, {"status": "UP", "db_host": DB_HOST, "db": db})
        elif self.path == "/notes":
            try:
                conn = connect()
                rows = conn.run("SELECT id, content, created_at FROM notes ORDER BY id")
                conn.close()
                self._send(200, [
                    {"id": r[0], "content": r[1], "created_at": str(r[2])} for r in rows
                ])
            except Exception as e:
                self._send(500, {"error": str(e)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/notes":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            content = data.get("content")
            if not content:
                self._send(400, {"error": "thieu truong content"})
                return
            conn = connect()
            rows = conn.run(
                "INSERT INTO notes (content) VALUES (:c) RETURNING id", c=content
            )
            conn.close()
            self._send(201, {"id": rows[0][0], "content": content})
        except Exception as e:
            self._send(500, {"error": str(e)})


if __name__ == "__main__":
    if not wait_for_db():
        print("Khong ket noi duoc database, thoat.", flush=True)
        sys.exit(1)
    init_db()
    print(f"Backend lang nghe tai 0.0.0.0:{PORT} (DB {DB_HOST}:{DB_PORT}/{DB_NAME})", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
