# Use Python 3.9 as the base image
FROM python:3.9-slim

# Install system dependencies for building Python packages (including dependencies for yarl)
RUN apt-get update && apt-get install -y \
    python3-dev \
    gcc \
    make \
    libc6-dev \
    libssl-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the required Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose a port if needed (e.g., for web servers)
# EXPOSE 5000

# Command to run on container start (if applicable)
CMD ["python", "main.py"]
