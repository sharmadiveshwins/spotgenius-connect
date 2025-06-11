#!/bin/bash

CONTAINER_NAME="spotgenius_connect_huey"
HEALTH_API_URL="http://localhost:8001/v1/health"
LOG_FILE="./logs/watchdog.log"

# Ensure log file exists
touch "$LOG_FILE"

while true; do
  # Check the health API
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_API_URL)
  if [ "$RESPONSE" -eq 200 ]; then
    echo "$(date): $CONTAINER_NAME is healthy." | tee -a "$LOG_FILE"
  elif [ "$RESPONSE" -eq 500 ]; then
    echo "$(date): $CONTAINER_NAME is unhealthy. Restarting..." | tee -a "$LOG_FILE"
    docker restart $CONTAINER_NAME
  else
    echo "$(date): $CONTAINER_NAME health check failed. Response code: $RESPONSE. Verifying container..." | tee -a "$LOG_FILE"

    # Verify container status if health check fails
    STATUS=$(docker inspect --format='{{.State.Status}}' $CONTAINER_NAME 2>/dev/null)
    if [ "$STATUS" == "exited" ] || [ "$STATUS" == "stopped" ]; then
      echo "$(date): Container $CONTAINER_NAME is stopped. Starting..." | tee -a "$LOG_FILE"
      docker start $CONTAINER_NAME
    elif [ -z "$STATUS" ]; then
      echo "$(date): Container $CONTAINER_NAME not found. Please verify the container name." | tee -a "$LOG_FILE"
    fi
  fi

  sleep 180  # Check every 3 minutes
done
