import requests
import time
import io
import json
from PIL import ImageGrab
from utils.debug_logger import logger


class DiscordNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url

    def set_webhook_url(self, webhook_url):
        self.webhook_url = webhook_url

    def send_notification(self, message, user_id=None, color=0x00ff00, include_screenshot=False):
        """Send a notification to Discord via webhook"""
        if not self.webhook_url:
            print("Discord webhook URL not set!")
            return False
        
        if include_screenshot:
            screenshot = ImageGrab.grab()

            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            buffer.seek(0)

        try:
            content = f"<@{user_id}>" if user_id else ""

            embed = {
                "title": "Dig Tool Notification",
                "description": message,
                "color": color,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
                "image": {
                    "url": "attachment://screenshot.png"
                } if include_screenshot else None
            }

            payload = {
                "content": content,
                "embeds": [embed]
            }

            files = {
                "payload_json": (None, json.dumps(payload), "application/json"),
                "file": ("screenshot.png", buffer, "image/png")
            } if include_screenshot else {}
            
            response = requests.post(
                self.webhook_url,
                files=files,
                timeout=10
            ) if include_screenshot else requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 204 or response.status_code == 200:
                print("Discord notification sent successfully")
                return True
            else:
                print(f"Discord notification failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"Error sending Discord notification: {e}")
            return False

    def send_startup_notification(self, user_id=None):
        """Send notification when bot starts"""
        return self.send_notification("🟢 Bot started and ready!", user_id, 0x00ff00)

    def send_shutdown_notification(self, user_id=None):
        """Send notification when bot stops"""
        return self.send_notification("🔴 Bot stopped.", user_id, 0xff0000)

    def send_milestone_notification(self, digs, clicks, user_id=None, include_screenshot=False):
        """Send notification for milestones"""
        message = f"📊 Milestone reached!\n**Digs:** {digs}\n**Clicks:** {clicks}"
        return self.send_notification(message, user_id, 0x0099ff, include_screenshot)

    def send_error_notification(self, error_message, user_id=None):
        """Send notification for errors"""
        message = f"⚠️ Error occurred: {error_message}"
        return self.send_notification(message, user_id, 0xff9900)

    def test_webhook(self, user_id=None, include_screenshot=False):
        """Test the webhook connection"""
        return self.send_notification("🧪 Test notification - Discord integration is working!", user_id, 0x9900ff, include_screenshot)
