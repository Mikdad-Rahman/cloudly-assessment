# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies needed by PyMuPDF
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Create necessary directories
RUN mkdir -p logs outputs/scenario_b_iter1 \
    outputs/scenario_b_iter2 \
    outputs/scenario_b_iter3

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Default command runs FastAPI
CMD ["python", "main.py", "--serve"]