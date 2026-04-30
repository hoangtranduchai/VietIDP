FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install system dependencies required by OCR/image libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY requirements.txt setup.py ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the canonical FastAPI application source
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
