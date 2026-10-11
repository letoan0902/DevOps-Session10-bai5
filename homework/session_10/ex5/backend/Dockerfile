# Image nền Python 3.12 bản alpine (nhỏ gọn)
FROM python:3.12-alpine

# Thư mục làm việc trong container
WORKDIR /app

# Cài driver PostgreSQL thuần Python (không cần thư viện C)
RUN pip install --no-cache-dir pg8000==1.31.2

# Chép mã nguồn ứng dụng vào image
COPY app.py .

# Cổng ứng dụng lắng nghe trong container
EXPOSE 8080

# Lệnh chạy khi container khởi động
CMD ["python", "app.py"]
