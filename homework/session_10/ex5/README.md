# Bài 5 - Tự động hóa điều phối đa dịch vụ với Docker Compose và tệp .env

Session 10 - DevOps. Đóng gói cụm Backend Web API + PostgreSQL của bài 4 thành một tệp `docker-compose.yml` theo chuẩn Infrastructure as Code, tách thông tin nhạy cảm ra tệp `.env`.

Toàn bộ lệnh trong báo cáo được chạy thật trên Windows 11, Docker Desktop (engine Linux), Docker Compose v5.5.0 (Compose CLI v2, gọi bằng `docker compose`), shell Git Bash. Output được chép nguyên văn từ `terminal_log.txt`.

## Mục lục

1. Mục tiêu
2. So sánh bài 4 (CLI thủ công) và bài 5 (Compose)
3. Kiến trúc
4. Cấu trúc thư mục
5. Giải thích `docker-compose.yml`
6. Cơ chế tệp `.env`
7. Các bước thực hiện và output thật
8. Bảng lệnh Docker Compose
9. Xử lý sự cố
10. Đối chiếu yêu cầu đề bài
11. Kết luận

---

## 1. Mục tiêu

- Viết `docker-compose.yml` khai báo 2 service: `backend` (Web API Python) và `database` (PostgreSQL 15).
- Khai báo `networks` và `volumes` ở cấp root để Compose tự tạo khi `up`.
- Tách tên DB, user, password, port ra tệp `.env`; cung cấp `.env.example` làm mẫu; chặn `.env` bằng `.gitignore`.
- Dùng `depends_on` để điều phối thứ tự khởi động, kết hợp `healthcheck` để backend chỉ chạy khi database đã sẵn sàng.
- Vận hành toàn bộ vòng đời bằng một nhóm lệnh `docker compose`: `up -d`, `ps`, `logs -f`, `down`.

Kết quả mong đợi: `docker compose up -d` tự tạo network, volume và đưa cả 2 dịch vụ lên trạng thái Running. Kết quả này đã đạt (mục 7.3).

## 2. So sánh bài 4 (CLI thủ công) và bài 5 (Compose)

Ở bài 4, hạ tầng được dựng bằng chuỗi lệnh `docker network create`, `docker volume create`, `docker run`. Mỗi lệnh phải gõ đúng thứ tự, đúng tham số; không có tệp nào lưu lại "trạng thái mong muốn" của hệ thống. Ở bài 5, toàn bộ được mô tả khai báo (declarative) trong một tệp YAML có thể đưa vào Git, và Compose tự suy ra các bước cần làm.

| Bài 4 (lệnh thủ công) | Bài 5 (khai báo trong Compose) |
|---|---|
| `docker network create app-net` | Khối `networks:` ở cấp root (`backend-net`), service gắn vào bằng `networks:` |
| `docker volume create db-data` | Khối `volumes:` ở cấp root (`pgdata`), service mount bằng `volumes:` |
| `docker run -d --name db-server --network app-net -v db-data:/var/lib/postgresql/data -e POSTGRES_...` | Service `database:` với `image`, `environment`, `volumes`, `networks` |
| `docker build -t ... .` rồi `docker run -d --name app-container -p 8084:8080 -e DB_HOST=... --network app-net ...` | Service `backend:` với `build`, `ports`, `environment`, `networks` |
| Tự nhớ chạy DB trước, chờ DB sẵn sàng rồi mới chạy app | `depends_on` + `healthcheck` (condition: service_healthy) |
| Dọn dẹp: `docker rm -f`, `docker network rm`, `docker volume rm` | `docker compose down` (hoặc `down -v`) |
| Mật khẩu viết thẳng vào dòng lệnh, nằm trong lịch sử shell | Mật khẩu nằm trong `.env`, không commit |

Tên tài nguyên cũng được chuẩn hóa: Compose đặt tiền tố theo tên project (tên thư mục `compose-stack`), nên ta có `compose-stack_backend-net`, `compose-stack_pgdata`, `compose-stack-database-1`, `compose-stack-backend-1`. Nhờ vậy nhiều project Compose có thể chạy song song trên cùng một máy mà không trùng tên.

## 3. Kiến trúc

```
                        May host (Windows 11 / Docker Desktop)
   +--------------------------------------------------------------------+
   |                                                                    |
   |   curl http://localhost:8085                                       |
   |            |                                                       |
   |            | (host:8085 -> container:8080)                         |
   |   +--------v------------------------------------------------+      |
   |   | network: compose-stack_backend-net (bridge, DNS theo ten)|      |
   |   |                                                          |      |
   |   |  +---------------------------+   +--------------------+  |      |
   |   |  | compose-stack-backend-1   |   | compose-stack-     |  |      |
   |   |  | service: backend          |   | database-1         |  |      |
   |   |  | python:3.12-alpine        |-->| service: database  |  |      |
   |   |  | Web API :8080             |   | postgres:15-alpine |  |      |
   |   |  | DB_HOST=database          |   | :5432 (healthy)    |  |      |
   |   |  +---------------------------+   +---------+----------+  |      |
   |   |        depends_on: service_healthy          |             |      |
   |   +---------------------------------------------|-------------+      |
   |                                                 |                    |
   |                                    +------------v-----------+        |
   |                                    | volume: compose-stack_ |        |
   |                                    | pgdata                 |        |
   |                                    | /var/lib/postgresql/   |        |
   |                                    | data                   |        |
   |                                    +------------------------+        |
   |                                                                      |
   |   .env (DB_NAME, DB_USER, DB_PASSWORD, DB_PORT, PORT)  -- noi suy -->|
   |   docker-compose.yml  (${DB_NAME}, ${PORT}, ...)                     |
   +--------------------------------------------------------------------+
```

Chỉ cổng 8085 của backend được mở ra host. Database không publish cổng nào (`5432/tcp` chỉ tồn tại bên trong network), nên chỉ backend trong cùng network `backend-net` truy cập được.

## 4. Cấu trúc thư mục

```
homework/session_10/ex5/
  docker-compose.yml     Khai báo hạ tầng (services, networks, volumes)
  .env.example           Tệp mẫu biến môi trường (placeholder, được commit)
  .gitignore             Chặn .env và *.log
  README.md              Báo cáo này
  terminal_log.txt       Log lệnh và output thật
  backend/
    Dockerfile           Image cho Web API
    app.py               Mã nguồn Web API (thư viện chuẩn + pg8000)
```

Tệp `.env` thật (chứa mật khẩu) nằm cạnh `docker-compose.yml` khi chạy, nhưng không có trong thư mục nộp.

Vì sao dùng `build: ./backend` thay vì `build: .` như mẫu của đề: đặt mã nguồn và Dockerfile của backend vào thư mục riêng giúp tách rõ "cấu hình hạ tầng" (compose, `.env`) khỏi "mã ứng dụng". Build context chỉ gồm thư mục `backend/` (ở lần build thật, context chỉ 3.91kB), không kéo theo `.env`, `.gitignore`, `README.md` vào context; sau này thêm service khác (frontend, worker) cũng chỉ cần thêm thư mục tương ứng.

## 5. Giải thích `docker-compose.yml`

Nội dung tệp:

```yaml
services:
  database:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks:
      - backend-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build: ./backend
    restart: unless-stopped
    ports:
      - "${PORT}:8080"
    environment:
      DB_HOST: database
      DB_PORT: ${DB_PORT}
      DB_NAME: ${DB_NAME}
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
    depends_on:
      database:
        condition: service_healthy
    networks:
      - backend-net

volumes:
  pgdata:

networks:
  backend-net:
```

(Bản đầy đủ có comment tiếng Việt nằm trong tệp `docker-compose.yml`.)

| Khóa | Ý nghĩa trong bài |
|---|---|
| `services` | Danh sách các dịch vụ (container) của ứng dụng. Mỗi khóa con (`database`, `backend`) là tên service, đồng thời là tên DNS trong network. |
| `image` | Dùng image có sẵn từ registry. `database` dùng `postgres:15-alpine`. |
| `build` | Build image từ Dockerfile thay vì kéo về. `build: ./backend` nghĩa là context và Dockerfile nằm trong thư mục `backend/`. Khi dùng cờ `--build`, Compose build lại image. |
| `environment` | Truyền biến môi trường vào container. Giá trị `${DB_NAME}` được Compose nội suy từ `.env` ngay lúc đọc tệp, trước khi tạo container. `DB_HOST: database` là giá trị cố định: tên service chính là hostname. |
| `ports` | Ánh xạ `host:container`. `"${PORT}:8080"` -> `8085:8080`. Phải đặt trong dấu nháy để YAML không hiểu nhầm. Database không có khóa này nên không lộ ra host. |
| `volumes` (trong service) | `pgdata:/var/lib/postgresql/data` gắn named volume vào thư mục dữ liệu của PostgreSQL để dữ liệu sống sót qua việc xóa container. |
| `networks` (trong service) | Gắn service vào network `backend-net`. Các service cùng network gọi nhau bằng tên service qua DNS nội bộ. |
| `depends_on` dạng ngắn | `depends_on: [database]` (như mẫu của đề): Compose chỉ đảm bảo container `database` được START trước container `backend`. Nó không chờ PostgreSQL thực sự sẵn sàng, nên backend vẫn có thể gặp lỗi "connection refused" trong vài giây đầu. |
| `depends_on` dạng dài | `database: condition: service_healthy`: Compose chờ cho tới khi healthcheck của `database` báo `healthy` rồi mới khởi động `backend`. Đây là điểm khác chính so với dạng ngắn, và là lý do bài này dùng dạng dài. |
| `healthcheck` | Lệnh Compose/Docker chạy định kỳ trong container để xác định trạng thái. `pg_isready -U ${DB_USER} -d ${DB_NAME}` trả về mã 0 khi PostgreSQL nhận kết nối. `interval: 5s` là chu kỳ kiểm tra, `timeout: 5s` là thời gian tối đa mỗi lần, `retries: 10` là số lần thất bại liên tiếp thì mới coi là `unhealthy`. |
| `restart: unless-stopped` | Tự khởi động lại container khi nó thoát bất thường hoặc khi Docker daemon khởi động lại, trừ khi người dùng chủ động dừng (`docker compose stop`). |
| `volumes` (cấp root) | Khai báo named volume `pgdata`. Compose tạo `compose-stack_pgdata` khi `up` lần đầu và giữ lại khi `down` thường. |
| `networks` (cấp root) | Khai báo network `backend-net`. Compose tạo `compose-stack_backend-net` (driver bridge) khi `up` và xóa khi `down`. |

Lưu ý: không đặt `container_name` để Compose tự đặt tên `<project>-<service>-<số thứ tự>`, tránh xung đột tên và cho phép scale (`--scale`) sau này. Thụt lề dùng 2 dấu cách; YAML cấm ký tự Tab nên đã kiểm tra `LC_ALL=C.UTF-8 grep -nP "\t" docker-compose.yml` không có kết quả.

## 6. Cơ chế tệp `.env`

### 6.1 Compose tự đọc `.env` như thế nào

- Khi chạy `docker compose ...`, Compose tìm tệp tên `.env` trong thư mục project (thư mục chứa `docker-compose.yml`, hoặc thư mục làm việc hiện tại) và nạp các cặp `KEY=VALUE` làm nguồn biến để nội suy `${KEY}` trong tệp compose.
- Không cần khai báo `env_file:` cho việc nội suy này. (`env_file:` là cơ chế khác: nó truyền nguyên cả tệp vào môi trường của container. Bài này cố ý không dùng, mà dùng `environment` với `${VAR}` để thấy rõ biến nào đi vào container nào.)
- Thứ tự ưu tiên khi cùng một biến xuất hiện ở nhiều nơi: biến trong shell (`export DB_NAME=...` hoặc `DB_NAME=... docker compose up`) cao hơn `.env`, và `.env` cao hơn giá trị mặc định trong cú pháp `${VAR:-default}`.

```
   shell (export / VAR=... docker compose ...)    uu tien cao nhat
        |
        v
   tep .env trong thu muc project
        |
        v
   gia tri mac dinh  ${VAR:-default}              uu tien thap nhat
```

- Cú pháp hữu ích: `${VAR:-mặc định}` (dùng mặc định khi biến rỗng/chưa đặt), `${VAR:?thông báo lỗi}` (dừng với lỗi khi thiếu biến, an toàn hơn so với việc để chuỗi rỗng).

### 6.2 Vì sao tách bí mật ra `.env` và dùng `.env.example`

- `docker-compose.yml` là tài sản hạ tầng, cần commit để cả nhóm dùng chung. Mật khẩu, tên user, cổng thay đổi theo từng máy/môi trường (dev, staging, production), không nên nằm cứng trong tệp được chia sẻ.
- `.env` chứa giá trị thật nên bị `.gitignore` chặn: không bao giờ lên GitHub. Nếu lỡ commit mật khẩu, nó nằm vĩnh viễn trong lịch sử Git.
- Tuy vậy vẫn cần nộp `.env.example`: đây là "hợp đồng" cho người khác biết dự án cần những biến nào (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `PORT`). Người mới chỉ cần `cp .env.example .env` rồi điền giá trị. Tệp mẫu chỉ chứa placeholder (`DB_PASSWORD=change_me`) nên không lộ bí mật.
- Lưu ý bảo mật: `docker compose config` in ra cấu hình đã nội suy nên mật khẩu hiện rõ (xem mục 7.1: `POSTGRES_PASSWORD: AppUser_2026`). Đây chính là lý do `.env` phải được bảo vệ, và không dán output `config` lên nơi công khai. Mật khẩu trong bài này là giá trị giả dùng cho bài tập.

## 7. Các bước thực hiện và output thật

Thư mục làm việc: `compose-stack/` (tên project = `compose-stack`). `.env` thật gồm 5 biến: `DB_NAME=appdb`, `DB_USER=appuser`, `DB_PASSWORD=AppUser_2026`, `DB_PORT=5432`, `PORT=8085`.

### 7.1 Kiểm tra phiên bản và cấu hình đã nội suy

```
$ docker compose version
Docker Compose version v5.5.0
```

`docker compose config` kiểm tra cú pháp và in cấu hình sau khi nội suy (trích phần quan trọng):

```
$ docker compose config
name: compose-stack
services:
  backend:
    build:
      context: D:\Rikkei\DevOps\Session10\_demo\bai5\compose-stack\backend
      dockerfile: Dockerfile
    depends_on:
      database:
        condition: service_healthy
        required: true
    environment:
      DB_HOST: database
      DB_NAME: appdb
      DB_PASSWORD: AppUser_2026
      DB_PORT: "5432"
      DB_USER: appuser
    networks:
      backend-net: null
    ports:
      - mode: ingress
        target: 8080
        published: "8085"
        protocol: tcp
    restart: unless-stopped
  database:
    environment:
      POSTGRES_DB: appdb
      POSTGRES_PASSWORD: AppUser_2026
      POSTGRES_USER: appuser
    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -U appuser -d appdb
      ...
```

Nhận xét: mọi `${...}` đã được thay bằng giá trị trong `.env` (`published: "8085"`, `pg_isready -U appuser -d appdb`). Mật khẩu hiện rõ, nhắc lại lý do không commit `.env`. Phần sau cùng của output cho thấy tên tài nguyên sẽ được tạo: `compose-stack_backend-net` và `compose-stack_pgdata`.

### 7.2 Thử nghiệm thiếu tệp `.env`

```
$ mv .env .env.bak
$ docker compose config 2>&1 | head -20
time="2026-10-12T04:10:03+07:00" level=warning msg="The \"DB_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2026-10-12T04:10:03+07:00" level=warning msg="The \"DB_NAME\" variable is not set. Defaulting to a blank string."
time="2026-10-12T04:10:03+07:00" level=warning msg="The \"DB_USER\" variable is not set. Defaulting to a blank string."
...
time="2026-10-12T04:10:03+07:00" level=warning msg="The \"PORT\" variable is not set. Defaulting to a blank string."
$ mv .env.bak .env
```

Giải thích: khi không có `.env` (và biến không có trong shell), Compose không báo lỗi mà thay bằng chuỗi rỗng và chỉ cảnh báo. Hậu quả nguy hiểm: image PostgreSQL sẽ không khởi tạo được vì mật khẩu rỗng, và ánh xạ cổng bị rỗng ở phía host (`":8080"`). Vì vậy phải đọc cảnh báo `variable is not set`, hoặc dùng `${VAR:?lỗi}` để bắt buộc phải có giá trị. Sau thử nghiệm đã `mv` trả lại `.env`.

### 7.3 `docker compose up -d --build`

Lệnh chạy với `--progress plain` để output không có ký tự động. Lưu ý `--progress` là cờ toàn cục nên đặt trước `up` (đặt sau `up` sẽ báo `unknown flag: --progress`). Trích phần quan trọng, toàn văn xem `terminal_log.txt`:

```
$ docker compose --progress plain up -d --build
 Image compose-stack-backend Building
#3 [internal] load metadata for docker.io/library/python:3.12-alpine
#5 [internal] load build context
#5 transferring context: 3.91kB done
#7 [2/4] WORKDIR /app
#8 [3/4] RUN pip install --no-cache-dir pg8000==1.31.2
#8 4.320 Successfully installed asn1crypto-1.5.1 pg8000-1.31.2 python-dateutil-2.9.0.post0 scramp-1.4.17 six-1.17.0
#9 [4/4] COPY app.py .
#10 naming to docker.io/library/compose-stack-backend:latest done
 Image compose-stack-backend Built
 Volume compose-stack_pgdata Creating
 Network compose-stack_backend-net Creating
 Volume compose-stack_pgdata Created
 Network compose-stack_backend-net Created
 Container compose-stack-database-1 Creating
 Container compose-stack-database-1 Created
 Container compose-stack-backend-1 Creating
 Container compose-stack-backend-1 Created
 Container compose-stack-database-1 Starting
 Container compose-stack-database-1 Started
 Container compose-stack-database-1 Waiting
 Container compose-stack-database-1 Healthy
 Container compose-stack-backend-1 Starting
 Container compose-stack-backend-1 Started
```

Quan sát thứ tự: Compose build image backend, tạo volume và network, tạo cả 2 container, khởi động `database`, ĐỢI (`Waiting`) tới khi `Healthy`, và chỉ sau đó mới `Starting` backend. Đây là tác dụng của `depends_on` dạng dài. Network và volume do Compose tự tạo, không cần lệnh riêng.

```
$ docker compose ps
NAME                       IMAGE                   COMMAND                  SERVICE    CREATED         STATUS                   PORTS
compose-stack-backend-1    compose-stack-backend   "python app.py"          backend    7 seconds ago   Up Less than a second    0.0.0.0:8085->8080/tcp, [::]:8085->8080/tcp
compose-stack-database-1   postgres:15-alpine      "docker-entrypoint.s..."   database   7 seconds ago   Up 6 seconds (healthy)   5432/tcp
```

Cả 2 service ở trạng thái Up; `database` có `(healthy)`; `backend` publish `0.0.0.0:8085->8080/tcp`; `database` chỉ có `5432/tcp` nội bộ, không publish. (Docker cắt cột COMMAND bằng ký tự "..." khi in ra terminal.)

```
$ docker network ls --filter name=compose-stack
NETWORK ID     NAME                        DRIVER    SCOPE
5187c378c50e   compose-stack_backend-net   bridge    local
$ docker volume ls --filter name=compose-stack
DRIVER    VOLUME NAME
local     compose-stack_pgdata
$ docker compose images
CONTAINER                  REPOSITORY              TAG                 PLATFORM            IMAGE ID            SIZE                CREATED
compose-stack-backend-1    compose-stack-backend   latest              linux/amd64         ff5ad385f504        24.8MB              10 seconds ago
compose-stack-database-1   postgres                15-alpine           linux/amd64         f7d23353e1b1        115MB               3 weeks ago
```

Network `compose-stack_backend-net` và volume `compose-stack_pgdata` đã được tạo tự động.

### 7.4 Xem log

`docker compose logs --tail=30` in 30 dòng cuối của mỗi service (trích):

```
$ docker compose logs --tail=30
...
database-1  | 2026-10-11 21:10:32.447 UTC [1] LOG:  database system is ready to accept connections
backend-1   | Backend lang nghe tai 0.0.0.0:8080 (DB database:5432/appdb)
```

Theo dõi liên tục bằng `docker compose logs -f` (khi gõ tay, nhấn Ctrl+C để dừng). Trong báo cáo chạy không tương tác nên dùng `timeout 8` để tự dừng sau 8 giây:

```
$ timeout 8 docker compose logs -f
backend-1  | Backend lang nghe tai 0.0.0.0:8080 (DB database:5432/appdb)
database-1  | The files belonging to this database system will be owned by user "postgres".
...
database-1  | CREATE DATABASE
...
database-1  | PostgreSQL init process complete; ready for start up.
...
database-1  | 2026-10-11 21:10:32.447 UTC [1] LOG:  database system is ready to accept connections
```

Log lần chạy đầu có `CREATE DATABASE` và `PostgreSQL init process complete`: PostgreSQL khởi tạo cụm dữ liệu mới và tạo database `appdb` từ biến `POSTGRES_DB`. Backend không in dòng `Dang cho database ...` vì nhờ `service_healthy` nó chỉ khởi động khi DB đã sẵn sàng, kết nối thành công ngay lần đầu.

### 7.5 Kiểm tra chức năng

```
$ curl -s http://localhost:8085/health
{"status": "UP", "db_host": "database", "db": "connected"}

$ curl -s -X POST -H 'Content-Type: application/json' -d '{"content":"Ghi chu dau tien"}' -w ' [HTTP %{http_code}]' http://localhost:8085/notes
{"id": 1, "content": "Ghi chu dau tien"} [HTTP 201]

$ curl -s -X POST -H 'Content-Type: application/json' -d '{"content":"Docker Compose chay that"}' -w ' [HTTP %{http_code}]' http://localhost:8085/notes
{"id": 2, "content": "Docker Compose chay that"} [HTTP 201]

$ curl -s http://localhost:8085/notes
[{"id": 1, "content": "Ghi chu dau tien", "created_at": "2026-10-11 21:10:56.437244+00:00"}, {"id": 2, "content": "Docker Compose chay that", "created_at": "2026-10-11 21:10:56.720422+00:00"}]
```

`/health` trả `"db": "connected"` và `"db_host": "database"`: backend đã phân giải tên `database` thành địa chỉ container DB qua DNS của network. Hai lệnh POST trả HTTP 201.

Đối chiếu trực tiếp trong PostgreSQL:

```
$ MSYS_NO_PATHCONV=1 docker compose exec database psql -U appuser -d appdb -c 'SELECT * FROM notes;'
 id |         content          |          created_at           
----+--------------------------+-------------------------------
  1 | Ghi chu dau tien         | 2026-10-11 21:10:56.437244+00
  2 | Docker Compose chay that | 2026-10-11 21:10:56.720422+00
(2 rows)
```

(`MSYS_NO_PATHCONV=1` ngăn Git Bash tự đổi các đường dẫn kiểu `/...` trong tham số.) Dữ liệu qua API khớp với dữ liệu trong bảng `notes`.

DNS theo tên service:

```
$ docker compose exec backend ping -c 2 database
PING database (172.20.0.2): 56 data bytes
64 bytes from 172.20.0.2: seq=0 ttl=64 time=0.076 ms
64 bytes from 172.20.0.2: seq=1 ttl=64 time=0.181 ms

--- database ping statistics ---
2 packets transmitted, 2 packets received, 0% packet loss
round-trip min/avg/max = 0.076/0.128/0.181 ms
```

Tên `database` (tên service trong Compose) phân giải thành `172.20.0.2`. Không cần biết hay cố định IP.

Log request của backend:

```
$ docker compose logs --tail=6 backend
backend-1  | Backend lang nghe tai 0.0.0.0:8080 (DB database:5432/appdb)
backend-1  | [11/Oct/2026 21:10:56] 172.20.0.1 "GET /health HTTP/1.1" 200 -
backend-1  | [11/Oct/2026 21:10:56] 172.20.0.1 "POST /notes HTTP/1.1" 201 -
backend-1  | [11/Oct/2026 21:10:56] 172.20.0.1 "POST /notes HTTP/1.1" 201 -
backend-1  | [11/Oct/2026 21:10:56] 172.20.0.1 "GET /notes HTTP/1.1" 200 -
```

### 7.6 Kiểm tra bền vững dữ liệu: `down` thường rồi `up` lại

```
$ docker compose down
 Container compose-stack-backend-1 Stopping
 Container compose-stack-backend-1 Stopped
 Container compose-stack-backend-1 Removing
 Container compose-stack-backend-1 Removed
 Container compose-stack-database-1 Stopping
 Container compose-stack-database-1 Stopped
 Container compose-stack-database-1 Removing
 Container compose-stack-database-1 Removed
 Network compose-stack_backend-net Removing
 Network compose-stack_backend-net Removed
$ docker compose ps
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
$ docker ps -a --filter name=compose-stack
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
$ docker network ls --filter name=compose-stack
NETWORK ID   NAME      DRIVER    SCOPE
$ docker volume ls --filter name=compose-stack
DRIVER    VOLUME NAME
local     compose-stack_pgdata
```

`down` xóa container và network, nhưng KHÔNG xóa volume `compose-stack_pgdata` (dòng cuối chứng minh volume còn). Chạy lại:

```
$ docker compose up -d
 Network compose-stack_backend-net Creating
 Network compose-stack_backend-net Created
 Container compose-stack-database-1 Creating
 Container compose-stack-database-1 Created
 Container compose-stack-backend-1 Creating
 Container compose-stack-backend-1 Created
 Container compose-stack-database-1 Starting
 Container compose-stack-database-1 Started
 Container compose-stack-database-1 Waiting
 Container compose-stack-database-1 Healthy
 Container compose-stack-backend-1 Starting
 Container compose-stack-backend-1 Started
$ curl -s http://localhost:8085/notes
[{"id": 1, "content": "Ghi chu dau tien", "created_at": "2026-10-11 21:10:56.437244+00:00"}, {"id": 2, "content": "Docker Compose chay that", "created_at": "2026-10-11 21:10:56.720422+00:00"}]
$ docker compose logs database | grep -n -E 'Skipping initialization|ready to accept'
2:database-1  | PostgreSQL Database directory appears to contain a database; Skipping initialization
9:database-1  | 2026-10-11 21:11:14.518 UTC [1] LOG:  database system is ready to accept connections
```

Lần này Compose chỉ cần tạo lại network (volume đã có, không còn dòng `Volume ... Created`). `GET /notes` vẫn trả đủ 2 bản ghi và log database ghi `Skipping initialization`: PostgreSQL nhận ra thư mục dữ liệu đã có sẵn trong volume và dùng lại. Dữ liệu sống sót qua vòng đời container.

### 7.7 Dọn dẹp: `down -v`

```
$ docker compose down -v
 Container compose-stack-backend-1 Stopping
 Container compose-stack-backend-1 Stopped
 Container compose-stack-backend-1 Removing
 Container compose-stack-backend-1 Removed
 Container compose-stack-database-1 Stopping
 Container compose-stack-database-1 Stopped
 Container compose-stack-database-1 Removing
 Container compose-stack-database-1 Removed
 Network compose-stack_backend-net Removing
 Volume compose-stack_pgdata Removing
 Volume compose-stack_pgdata Removed
 Network compose-stack_backend-net Removed
$ docker compose ps
NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
$ docker volume ls --filter name=compose-stack
DRIVER    VOLUME NAME
$ docker network ls --filter name=compose-stack
NETWORK ID   NAME      DRIVER    SCOPE
```

Thêm cờ `-v` làm Compose xóa luôn volume `compose-stack_pgdata` (dữ liệu mất vĩnh viễn). `ps` rỗng, không còn volume/network của project. Image `compose-stack-backend:latest` được giữ lại để dùng cho lần chạy sau.

## 8. Bảng lệnh Docker Compose

| Lệnh | Tác dụng |
|---|---|
| `docker compose version` | Xem phiên bản Compose |
| `docker compose config` | Kiểm tra cú pháp, in cấu hình đã nội suy biến (có lộ bí mật) |
| `docker compose config -q` | Chỉ kiểm tra hợp lệ, không in nội dung |
| `docker compose up -d` | Tạo network/volume/container nếu chưa có và chạy nền |
| `docker compose up -d --build` | Như trên, nhưng build lại image của service có `build:` |
| `docker compose ps` | Liệt kê container của project, trạng thái, cổng |
| `docker compose ps --format json` | Xuất trạng thái dạng JSON |
| `docker compose logs [service]` | Xem log |
| `docker compose logs -f` | Theo dõi log liên tục (Ctrl+C để dừng) |
| `docker compose logs --tail=30` | Chỉ lấy 30 dòng cuối mỗi service |
| `docker compose exec <service> <lệnh>` | Chạy lệnh trong container đang chạy |
| `docker compose stop` / `start` | Dừng / chạy lại container (không xóa) |
| `docker compose restart <service>` | Khởi động lại service |
| `docker compose images` | Liệt kê image đang dùng |
| `docker compose down` | Dừng và xóa container + network; GIỮ volume |
| `docker compose down -v` | Như trên và xóa cả named volume (mất dữ liệu) |
| `docker compose -f <tệp> ...` | Chỉ định tệp compose khác |
| `docker compose --progress plain ...` | Output dạng văn bản thuần (cờ toàn cục, đặt trước lệnh con) |

## 9. Xử lý sự cố

| Sự cố | Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|---|
| Biến không được đặt | `The "DB_NAME" variable is not set. Defaulting to a blank string.` (đã gặp ở mục 7.2) | Thiếu `.env`, sai tên tệp, hoặc chạy lệnh ngoài thư mục project | Tạo `.env` từ `.env.example`, chạy lệnh trong thư mục chứa compose; dùng `${VAR:?lỗi}` để bắt buộc có giá trị |
| Cổng đã bị chiếm | `Bind for 0.0.0.0:8085 failed: port is already allocated` | Một container/tiến trình khác đã dùng cổng host đó | Đổi `PORT` trong `.env` (ví dụ 8086) rồi `docker compose up -d` lại; tìm bên đang giữ cổng bằng `docker ps` hoặc `netstat` |
| Backend khởi động trước DB khi dùng `depends_on` dạng ngắn | Log backend có lỗi kết nối, `connection refused`, hoặc container thoát | Dạng ngắn chỉ đảm bảo thứ tự START, không chờ PostgreSQL sẵn sàng | Dùng dạng dài `condition: service_healthy` kèm `healthcheck` (như bài này); app nên có vòng thử lại kết nối (`app.py` thử tối đa 30 lần, in `Dang cho database ...`) |
| Lỗi thụt lề YAML | Ví dụ đã chạy thật: `go-yaml load error in parser (while parsing a block mapping) at L2.C3-L4.C4: did not find expected key` (do khóa `environment` lệch 1 dấu cách so với các khóa cùng cấp) | Thụt lề không đều, dùng Tab, hoặc thiếu dấu nháy | Dùng đúng 2 dấu cách, không dùng Tab (`grep -nP "\t"`), chạy `docker compose config -q` trước khi `up` |
| Mất dữ liệu sau khi dọn dẹp | `GET /notes` trả danh sách rỗng, log DB có `CREATE DATABASE` mới | Đã chạy `down -v` (xóa volume) | Dùng `down` thường nếu muốn giữ dữ liệu; chỉ dùng `down -v` khi chủ ý xóa sạch |
| `down` không xóa volume | `docker volume ls` vẫn còn `compose-stack_pgdata` | Hành vi mặc định có chủ đích để bảo vệ dữ liệu | Thêm `-v` nếu muốn xóa; hoặc `docker volume rm compose-stack_pgdata` |
| Đổi mật khẩu trong `.env` nhưng DB vẫn dùng mật khẩu cũ | Backend báo lỗi xác thực | `POSTGRES_PASSWORD` chỉ được áp dụng lần khởi tạo đầu tiên, khi volume còn trống | `docker compose down -v` để khởi tạo lại, hoặc đổi mật khẩu bằng `ALTER USER` |
| Đã commit nhầm `.env` | Mật khẩu hiện trong lịch sử Git | `.gitignore` chỉ có tác dụng với tệp chưa được theo dõi | `git rm --cached .env`, đổi mật khẩu, và làm sạch lịch sử nếu đã đẩy lên remote |

## 10. Đối chiếu yêu cầu đề bài

| Yêu cầu | Đáp ứng | Bằng chứng |
|---|---|---|
| `docker-compose.yml` khai báo 2 services `backend` và `database` | Đạt | Mục 5; `docker compose ps` thấy `compose-stack-backend-1` và `compose-stack-database-1` |
| Tách thông tin nhạy cảm (DB name, user, password, port) ra `.env` | Đạt | Compose dùng `${DB_NAME}`, `${DB_USER}`, `${DB_PASSWORD}`, `${DB_PORT}`, `${PORT}`; `docker compose config` nội suy đúng (mục 7.1) |
| Có `.env.example` | Đạt | Tệp mẫu chỉ chứa placeholder, kèm comment |
| `depends_on` | Đạt | Dạng dài với `service_healthy` (mục 5, 7.3) |
| `networks` ở cấp root | Đạt | `backend-net`; thực tế tạo `compose-stack_backend-net` |
| `volumes` ở cấp root | Đạt | `pgdata`; thực tế tạo `compose-stack_pgdata` |
| Chỉ dùng Docker Compose CLI v2 (`docker compose`) | Đạt | Mọi thao tác dùng `docker compose` (Compose v5.5.0); không dùng `docker-compose` |
| `docker compose up -d` tự tạo network, volume, đưa 2 dịch vụ lên Running | Đạt | Output mục 7.3: `Volume ... Created`, `Network ... Created`, 2 container Started, `ps` thấy Up và `(healthy)` |
| `docker compose ps` | Đạt | Mục 7.3 |
| `docker compose logs -f` | Đạt | Mục 7.4 (chạy với `timeout 8`) |
| `docker compose down` | Đạt | Mục 7.6 (giữ volume) và 7.7 (`down -v`) |
| Nộp `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md` | Đạt | Có đủ trong `homework/session_10/ex5/`, kèm `backend/` và `terminal_log.txt`; không nộp `.env` thật |

## 11. Kết luận

- Một tệp `docker-compose.yml` thay thế cả chuỗi lệnh `docker network create`, `docker volume create`, `docker run` của bài 4: hạ tầng trở thành mã có thể review, versioning và tái tạo bằng một lệnh `docker compose up -d`.
- Tệp `.env` giúp tách cấu hình theo môi trường và giữ bí mật ngoài Git; `.env.example` ghi lại danh sách biến cần thiết mà không lộ giá trị. Cần nhớ Compose chỉ cảnh báo (không lỗi) khi thiếu biến, và `docker compose config` hiển thị cả mật khẩu.
- `depends_on` dạng ngắn chỉ điều phối thứ tự start; kết hợp `healthcheck` với `condition: service_healthy` mới đảm bảo backend chỉ chạy khi database thật sự sẵn sàng. Thực nghiệm cho thấy backend kết nối được ngay lần đầu, không phải chờ.
- Named volume giữ dữ liệu qua `down`/`up` (2 bản ghi vẫn còn, log DB có `Skipping initialization`); chỉ `down -v` mới xóa dữ liệu. Cần phân biệt rõ hai lệnh này khi vận hành.
- Sau khi kiểm thử, toàn bộ tài nguyên của project `compose-stack` (container, network, volume) đã được dọn bằng `docker compose down -v`; image `compose-stack-backend` được giữ lại.
