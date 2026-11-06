# PolicyDrift API for a free Hugging Face Space (Docker SDK, CPU basic: 2 vCPU, 16 GB RAM).
# The embedding model and the chunk vectors are built into the image, so the first question is fast.
FROM python:3.12-slim

ENV PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    HF_HOME=/app/.cache/hf \
    POLICYDRIFT_ROOT=/app

RUN pip install --no-cache-dir uv==0.13.6
WORKDIR /app

# Dependencies first (CPU-only torch keeps the image small).
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-install-project \
 && uv pip install --no-cache torch --index-url https://download.pytorch.org/whl/cpu --reinstall \
 && uv sync --frozen --no-dev --inexact

COPY api ./api
COPY configs/models.yaml ./configs/models.yaml
COPY data/schemes.yaml ./data/schemes.yaml
COPY data/processed ./data/processed
COPY data/benchmark/dev ./data/benchmark/dev
COPY paper ./paper

# Download the model and embed the 440 chunks at build time. Only the dev split is shipped;
# the test split never leaves the research repository.
RUN uv run --no-sync python -c "from pathlib import Path; from policydrift.demo import DemoService; DemoService(Path('.')).retriever.search('warm-up', 1)"

ENV HF_HUB_OFFLINE=1
# Hugging Face Spaces run containers as user 1000.
RUN useradd -m -u 1000 app && chown -R app /app
USER app
EXPOSE 7860
CMD ["uv", "run", "--no-sync", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
