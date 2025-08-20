#!/bin/sh

# Function to check if running in ECS
is_running_in_ecs() {
  # Try to access the ECS metadata endpoint with a 1 second timeout
  if curl -s --connect-timeout 1 http://169.254.170.2 > /dev/null 2>&1; then
    echo "Running in ECS environment"
    return 0
  else
    echo "Not running in ECS environment"
    return 1
  fi
}

# Function to fetch region
fetch_region() {

  #Set region as var environment
  export AWS_REGION=$(curl -s 169.254.169.254/latest/meta-data/placement/region || echo "us-east-1")
}

# Function to cleanup processes
cleanup() {
  echo "Cleaning up processes..."
  if [ -n "$APP_PID" ]; then
    kill $APP_PID 2>/dev/null || true
  fi
  exit 0
}

# Trap signals for graceful shutdown
trap cleanup TERM INT

echo "Starting Nova Sonic WebSocket Server"

# Check if running in ECS and fetch initial credentials if so
if is_running_in_ecs; then
  # Initial startup - just set initial credentials
  fetch_region
  echo "Using on-demand credential refresh (triggered by ExpiredToken errors)"
else
  echo "Skipping credential refresh - not in ECS environment"
fi

# Set PYTHONPATH to include the current directory for module imports
export PYTHONPATH="${PYTHONPATH}:/app"

if [ "$DEV_MODE" = "true" ]; then
  echo "Running in DEV_MODE with inotifywait..."

  # Start the initial process
  python websocket_server.py &
  APP_PID=$!

  # Monitor directory for changes
  while true; do
    inotifywait -r -e modify,create,delete /app --format "%e %w%f"
    echo "Change detected, restarting process..."

    # Kill the previous process if it exists
    if [ -n "$APP_PID" ]; then
      kill $APP_PID 2>/dev/null || true
      wait $APP_PID 2>/dev/null || true
    fi

    # Start the process again
    python websocket_server.py &
    APP_PID=$!
  done
else
  echo "Running in production mode..."
  python websocket_server.py &
  APP_PID=$!
  
  # Wait for the application process
  wait $APP_PID
fi
