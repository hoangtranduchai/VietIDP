# Use Python 3.10 and Node 20 as base
FROM nikolaik/python-nodejs:python3.10-nodejs20

WORKDIR /app

# Install system dependencies required for OpenCV + PaddleOCR
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/package*.json ./backend/
RUN cd backend && npm install

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ai/ ./ai/
COPY src/ ./src/
COPY backend/ ./backend/
COPY setup.py ./
COPY .env.example ./.env

# Install src as package
RUN pip install -e .

# Expose backend API port
EXPOSE 5000

# Set environment to production
ENV NODE_ENV=production

# Start Node.js server
CMD ["node", "backend/index.js"]
