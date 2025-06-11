#!/bin/bash

HEALTH_URL="http://spot_connect:8001/api/v1/health"

# Slack notification function
notify_slack() {
  if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "SLACK_BOT_TOKEN not set, skipping Slack notification"
  else
    curl -s -X POST https://slack.com/api/chat.postMessage \
      -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
      -H "Content-Type: application/json; charset=utf-8" \
      --data "{
        \"channel\": \"$SLACK_CHANNEL_NAME\",
        \"text\": \"$1\"
      }" > /dev/null
  fi
}

# Notify container startup
notify_slack "🔄 Huey worker container started/restarted."

# Background health monitor loop
(
  LAST_STATUS=200
  while true; do
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")

    if [ "$STATUS_CODE" -ne 200 ]; then
      if [ "$LAST_STATUS" -eq 200 ]; then
        echo "❌ Health check failed. Status: $STATUS_CODE"
        notify_slack ":x: Health check failed for Huey worker container. Status: $STATUS_CODE"
      fi
    else
      if [ "$LAST_STATUS" -ne 200 ]; then
        echo "✅ Health check recovered."
        notify_slack ":white_check_mark: Health check recovered for Huey worker container."
      fi
    fi

    LAST_STATUS=$STATUS_CODE
    sleep 60
  done
) &

# Start Huey worker in foreground
exec huey_consumer.py app.main.huey --workers 3
