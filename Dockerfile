FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY atlas_log_analyzer/ atlas_log_analyzer/
CMD ["python", "-m", "atlas_log_analyzer"]
