# One container: builds the frontend, serves it and the API from one origin.
# Hugging Face Spaces (Docker SDK, port 7860) or any host with >= 4 GB RAM.
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/
RUN cd backend && UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-install-project
ENV PATH="/opt/venv/bin:$PATH" HF_HOME=/opt/hf
# Bake the three pretrained models into the image so the first request is not slow.
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
from transformers import pipeline
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
for m in ("cardiffnlp/twitter-roberta-base-sentiment-latest", "j-hartmann/emotion-english-distilroberta-base"):
    pipeline("text-classification", model=m)
PY
COPY backend/ backend/
COPY data/kb data/kb
COPY --from=web /web/dist frontend/dist
# ALLOWED_HOSTS defaults to every host because the platform proxy sets the public name; set it to your domain to tighten.
ENV ALLOWED_HOSTS="*" PORT=7860
EXPOSE 7860
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
