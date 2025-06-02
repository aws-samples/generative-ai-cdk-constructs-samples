FROM gradle:8.6.0-jdk21 AS build

WORKDIR /app
COPY . .
# Ensure we build a proper executable JAR with manifest
RUN gradle build --no-daemon

FROM eclipse-temurin:21.0.2_13-jre-jammy

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY --from=build /app/app/build/libs/*.jar app.jar

# Update system packages to fix vulnerabilities
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV AWS_REGION=us-east-1
ENV PORT=8080
ENV LOG_LEVEL=INFO
ENV CORS_ALLOWED_ORIGINS=*
ENV COGNITO_USER_POOL_ID=""
ENV AWS_ACCESS_KEY_ID=""
ENV AWS_SECRET_ACCESS_KEY=""
ENV AWS_SESSION_TOKEN=""
ENV DEPLOYMENT_TYPE="remote"

# Change ownership of the application files to the non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD curl -f http://localhost:${PORT}/health || exit 1

# Start Java WebSocket server
CMD ["java", "-jar", "app.jar"]
