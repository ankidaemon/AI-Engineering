FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY src ./src

# FAISS index + uploaded documents live here (mounted as a volume in compose)
RUN mkdir -p data/faiss_index data/uploads

EXPOSE 8090
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8090"]
