FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHROME_BIN=/usr/bin/chromium \
    DEBIAN_FRONTEND=noninteractive

# Install Chromium and necessary system fonts for PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    fonts-dejavu-core \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and root runner
COPY src/ ./src/
COPY main.py .

# Create output folder and expose volume
RUN mkdir -p /app/output
VOLUME ["/app/output"]

# Set default execution
ENTRYPOINT ["python", "main.py"]
CMD ["--output-dir", "/app/output"]
