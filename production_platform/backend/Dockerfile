FROM python:3.11-slim

WORKDIR /app

# System deps needed to build hmmlearn, arch, scipy wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache — only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Pre-bake Chronos T5-Small into the image ──────────────────────────────────
# Without this the first prediction request downloads ~300 MB from HuggingFace,
# causing a cold-start timeout on Render. Baking it here adds ~300 MB to the
# image but makes the first request respond in seconds instead of minutes.
RUN python -c "\
from chronos import ChronosPipeline; \
import torch; \
ChronosPipeline.from_pretrained('amazon/chronos-t5-small', device_map='cpu', torch_dtype=torch.float32); \
print('Chronos T5-Small cached successfully')"

# Copy application code
COPY . .

EXPOSE 8000

# Use shell form so $PORT is expanded at runtime (Render injects PORT env var)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
