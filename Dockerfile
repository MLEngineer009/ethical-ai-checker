FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Run application
COPY start.sh .
RUN chmod +x start.sh
CMD ["./start.sh"]
