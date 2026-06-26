FROM python:3.11-slim

# System libraries Pillow needs if it ever has to compile from source —
# belt-and-suspenders in case a future dependency bump again lacks a
# prebuilt wheel for whatever Python version this image ships.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "poller.py"]
