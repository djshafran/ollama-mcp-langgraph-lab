FROM python:3.11-slim

WORKDIR /app

COPY src/l0/core /app/src/l0/core
RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir fastmcp /app/src/l0/core \
 && pip install --no-cache-dir heritage

COPY src/l0/server/server.py /app/server.py

EXPOSE 8000
CMD ["python", "/app/server.py"]
