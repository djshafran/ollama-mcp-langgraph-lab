FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir fastmcp

COPY server.py /app/server.py

EXPOSE 8000
CMD ["python", "/app/server.py"]
