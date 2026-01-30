# Use Python 3.12 slim image for BedrockAgentCore
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy all agent source files
COPY agent.py .
COPY config.py .
COPY memory.py .
COPY tools.py .

# Set environment variables for BedrockAgentCore
ENV PYTHONUNBUFFERED=1

# Run the agent - BedrockAgentCoreApp handles the HTTP server
CMD ["python", "agent.py"]
