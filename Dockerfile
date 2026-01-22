FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed (none strictly required for this simple mock, but good practice)
# RUN apt-get update && apt-get install -y gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python"]
