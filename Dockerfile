# Use official Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
  gcc \
  python3-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt to the container and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clean up build dependencies to minimize image size
RUN apt-get purge -y --auto-remove gcc python3-dev

# Copy the entire project directory to the container
COPY . .

# Run the bot using run.py
CMD ["python", "run.py"]