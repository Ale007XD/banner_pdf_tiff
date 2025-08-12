FROM python:3.10-slim

# Install ghostscript
RUN apt-get update && apt-get install -y ghostscript && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create empty profiles directory
RUN mkdir -p /app/profiles

# Set command
CMD ["python", "-m", "src.main"]
