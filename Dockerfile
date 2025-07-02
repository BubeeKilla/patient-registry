# Use official lightweight Python image
FROM python:3.12-slim

# Set environment variables for clean output & no .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose port that Flask uses
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]
