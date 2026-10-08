FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt && useradd --create-home appuser
COPY backend /app/backend
COPY data /app/data
COPY ml/artifacts /app/ml/artifacts
COPY ml/escalation /app/ml/escalation
RUN mkdir -p /app/storage && chown -R appuser:appuser /app
USER appuser
WORKDIR /app/backend
ENV DATABASE_URL=sqlite:////app/storage/opspilot.db
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
