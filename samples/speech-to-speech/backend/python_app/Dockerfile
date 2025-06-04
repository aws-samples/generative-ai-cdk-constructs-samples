FROM python:3.13-alpine

WORKDIR /app

# Copy requirements file
COPY requirements.txt ./

# Install dependencies
RUN apk add --update jq curl py-pip inotify-tools
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN addgroup -S appuser && adduser -S appuser -G appuser

# Copy all Python files, directories, and entrypoint.sh
# Refactored structure includes core/, clients/, events/, tools/ directories
COPY . .

# Set environment variables
ENV LOGLEVEL=INFO
ENV HOST=0.0.0.0
ENV PORT=8080
ENV AWS_DEFAULT_REGION=us-east-1
ENV PYTHONPATH=/app

# Set execute permission for entrypoint.sh
RUN chmod +x entrypoint.sh

# Change ownership of the application files to the non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose single port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD curl -f http://localhost:${PORT}/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
