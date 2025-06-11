import json
import requests
import hashlib
import traceback
from app.config import settings


def send_slack_notification(title, message, mention_members=None, is_important=False):

    if mention_members:
        mentions = " ".join([f"<@{member}>" for member in mention_members])
        message = f"{message} | {mentions}"

    slack_data = {
        "channel": settings.SLACK_CHANNEL_NAME,
        "text": f"*{settings.ENVIRONMENT.upper()} : {title}*",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{settings.ENVIRONMENT.upper()} : {title}*\n{message}"
                }
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"
    }

    response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, data=json.dumps(slack_data))

    if response.status_code != 200 or not response.json().get("ok"):
        raise Exception(f"Slack API error: {response.status_code}, {response.text}")


def get_error_fingerprint(error):
    """Create a unique hash based on the error traceback only."""
    tb_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    error_hash = hashlib.md5(tb_str.encode()).hexdigest()
    return f"huey_alert:{error_hash[:10]}"
