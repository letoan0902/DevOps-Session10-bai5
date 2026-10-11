# DevOps - Session 10 - Bài 5

Tự động hóa điều phối đa dịch vụ với Docker Compose và tệp `.env`.

Đóng gói cụm Backend Web API (Python) + PostgreSQL của bài 4 thành `docker-compose.yml` theo chuẩn Infrastructure as Code, tách thông tin nhạy cảm ra `.env`, thao tác hoàn toàn bằng `docker compose` (Compose CLI v2).

Báo cáo chi tiết: [homework/session_10/ex5/README.md](homework/session_10/ex5/README.md)

## Danh sách file

| Đường dẫn | Mô tả |
|---|---|
| `homework/session_10/ex5/docker-compose.yml` | Khai báo 2 service `backend`, `database`, cùng `networks` và `volumes` ở cấp root |
| `homework/session_10/ex5/.env.example` | Tệp mẫu biến môi trường (placeholder) |
| `homework/session_10/ex5/.gitignore` | Chặn `.env` và `*.log` |
| `homework/session_10/ex5/backend/Dockerfile` | Image cho Backend Web API |
| `homework/session_10/ex5/backend/app.py` | Mã nguồn Web API (`/health`, `/notes`) |
| `homework/session_10/ex5/README.md` | Báo cáo bài làm |
| `homework/session_10/ex5/terminal_log.txt` | Log lệnh và output thật |

## Chạy nhanh

```
cd homework/session_10/ex5
cp .env.example .env      # rồi sửa giá trị trong .env
docker compose up -d --build
docker compose ps
curl http://localhost:8085/health
docker compose down
```
