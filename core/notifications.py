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
        if not self.webhook_url:
            logger.warning("Discord webhook URL not set!")
            return False
          
        buffer = None
        if include_screenshot:
            try:
                screenshot = ImageGrab.grab()
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                buffer.seek(0)
            except Exception as e:
                logger.error(f"Error capturing screenshot: {e}")
                include_screenshot = False

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

            if include_screenshot and buffer:
                files = {
                    "payload_json": (None, json.dumps(payload), "application/json"),
                    "file": ("screenshot.png", buffer, "image/png")
                }
                response = requests.post(
                    self.webhook_url,
                    files=files,
                    timeout=10
                )
            else:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

            if response.status_code == 204 or response.status_code == 200:
                logger.info("Discord notification sent successfully")
                return True
            else:
                logger.error(f"Discord notification failed: {response.status_code}")
                return False
              
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False
        finally:
            if buffer:
                try:
                    buffer.close()
                except:
                    pass

    def send_startup_notification(self, user_id=None):
        return self.send_notification("🟢 Bot started and ready!", user_id, 0x00FF00)

    def send_shutdown_notification(self, user_id=None):
        return self.send_notification("🔴 Bot stopped.", user_id, 0xFF0000)

    def send_milestone_notification(self, digs, clicks, user_id=None, include_screenshot=False):
        message = f"📊 Milestone reached!\n**Digs:** {digs}\n**Clicks:** {clicks}"
        return self.send_notification(message, user_id, 0x0099ff, include_screenshot)


    def send_error_notification(self, error_message, user_id=None):
        message = f"⚠️ Error occurred: {error_message}"
        return self.send_notification(message, user_id, 0xFF9900)

    def test_webhook(self, user_id=None, include_screenshot=False):
        return self.send_notification("🧪 Test notification - Discord integration is working!", user_id, 0x9900ff, include_screenshot)


def test_discord_ping(dig_tool_instance):
    try:
        import tkinter as tk
        webhook_url = dig_tool_instance.param_vars.get('webhook_url', tk.StringVar()).get()
        include_screenshot = dig_tool_instance.param_vars.get('include_screenshot_in_discord', tk.BooleanVar()).get()
        user_id = dig_tool_instance.param_vars.get('user_id', tk.StringVar()).get()

        if not webhook_url:
            dig_tool_instance.update_status("Webhook URL not set!")
            return

        dig_tool_instance.update_status("Testing Discord ping...")
        dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)

        import threading
        
        def test_and_report():
            try:
                success = dig_tool_instance.discord_notifier.test_webhook(user_id if user_id else None, include_screenshot)
                if success:
                    dig_tool_instance.update_status("Discord ping test completed successfully!")
                else:
                    dig_tool_instance.update_status("Discord ping test failed!")
            except Exception as e:
                dig_tool_instance.update_status(f"Discord ping test error: {e}")
                logger.error(f"Discord ping test error: {e}")
        
        threading.Thread(target=test_and_report, daemon=True).start()

    except Exception as e:
        dig_tool_instance.update_status(f"Discord ping test error: {e}")


def check_milestone_notifications(dig_tool_instance):
    try:
        import tkinter as tk
        import threading
        webhook_url = dig_tool_instance.param_vars.get('webhook_url', tk.StringVar()).get()
        include_screenshot = dig_tool_instance.param_vars.get('include_screenshot_in_discord', tk.BooleanVar()).get()
        user_id = dig_tool_instance.param_vars.get('user_id', tk.StringVar()).get()
        milestone_interval = dig_tool_instance.param_vars.get('milestone_interval', tk.IntVar()).get()

        if not webhook_url:
            logger.debug("Milestone notification skipped: No webhook URL set")
            return
            
        if milestone_interval <= 0:
            logger.debug("Milestone notification skipped: Invalid milestone interval")
            return

        if (
            dig_tool_instance.dig_count > 0
            and dig_tool_instance.dig_count % milestone_interval == 0
            and dig_tool_instance.dig_count != dig_tool_instance.last_milestone_notification
        ):
            logger.info(f"Sending milestone notification for {dig_tool_instance.dig_count} digs")
            dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
            
            def send_milestone():
                try:
                    success = dig_tool_instance.discord_notifier.send_milestone_notification(
                        dig_tool_instance.dig_count,
                        dig_tool_instance.click_count,
                        user_id if user_id else None,
                        include_screenshot
                    )
                    if success:
                        logger.info(f"Milestone notification sent successfully for {dig_tool_instance.dig_count} digs")
                    else:
                        logger.error(f"Failed to send milestone notification for {dig_tool_instance.dig_count} digs")
                except Exception as e:
                    logger.error(f"Error in milestone notification thread: {e}")
            
            threading.Thread(target=send_milestone, daemon=True).start()
            dig_tool_instance.last_milestone_notification = dig_tool_instance.dig_count

    except Exception as e:
        logger.error(f"Error in check_milestone_notifications: {e}")
        dig_tool_instance.update_status(f"Milestone notification error: {e}")


def send_startup_notification(dig_tool_instance):
    try:
        import tkinter as tk
        import threading
        webhook_url = dig_tool_instance.param_vars.get("webhook_url", tk.StringVar()).get()
        user_id = dig_tool_instance.param_vars.get("user_id", tk.StringVar()).get()
        if webhook_url:
            dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
            
            def send_startup():
                try:
                    success = dig_tool_instance.discord_notifier.send_startup_notification(user_id)
                    if success:
                        logger.info("Startup notification sent successfully")
                    else:
                        logger.error("Failed to send startup notification")
                except Exception as e:
                    logger.error(f"Error in startup notification thread: {e}")
            
            threading.Thread(target=send_startup, daemon=True).start()
        else:
            logger.debug("Startup notification skipped: No webhook URL set")
    except Exception as e:
        logger.error(f"Error in send_startup_notification: {e}")


def send_shutdown_notification(dig_tool_instance):
    try:
        import tkinter as tk
        import threading
        webhook_url = dig_tool_instance.param_vars.get("webhook_url", tk.StringVar()).get()
        user_id = dig_tool_instance.param_vars.get("user_id", tk.StringVar()).get()
        if webhook_url:
            dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
            
            def send_shutdown():
                try:
                    success = dig_tool_instance.discord_notifier.send_shutdown_notification(user_id)
                    if success:
                        logger.info("Shutdown notification sent successfully")
                    else:
                        logger.error("Failed to send shutdown notification")
                except Exception as e:
                    logger.error(f"Error in shutdown notification thread: {e}")
            
            threading.Thread(target=send_shutdown, daemon=True).start()
        else:
            logger.debug("Shutdown notification skipped: No webhook URL set")
    except Exception as e:
        logger.error(f"Error in send_shutdown_notification: {e}")
