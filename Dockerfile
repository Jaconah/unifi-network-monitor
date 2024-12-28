FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY unifi-network-monitor.py .

# Create volume mount point for persistent data
VOLUME ["/app/data"]

# Run the application
CMD ["python", "unifi-network-monitor.py"]