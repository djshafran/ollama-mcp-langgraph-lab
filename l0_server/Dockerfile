FROM python:3.11-slim

WORKDIR /app

COPY l0_core /app/l0_core
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir fastmcp /app/l0_core

COPY l0_server/server.py /app/server.py

EXPOSE 8000
CMD ["python", "/app/server.py"]
