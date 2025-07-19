import requests
import time
import io
import json
import threading
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
                    str(self.webhook_url),
                    files=files,
                    timeout=10
                )
            else:
                response = requests.post(
                    str(self.webhook_url),
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
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def _send_webhook_request(self, payload, include_screenshot=False):
        try:
            buffer = None
            files = {}
            
            if include_screenshot:
                try:
                    screenshot = ImageGrab.grab()
                    buffer = io.BytesIO()
                    screenshot.save(buffer, format='PNG')
                    buffer.seek(0)
                except Exception as e:
                    logger.error(f"Error capturing screenshot: {e}")
                    include_screenshot = False
            
            if include_screenshot and buffer:
                files = {
                    "payload_json": (None, json.dumps(payload), "application/json"),
                    "file": ("screenshot.png", buffer, "image/png")
                }
                response = requests.post(
                    str(self.webhook_url),
                    files=files,
                    timeout=10
                )
            else:
                response = requests.post(
                    str(self.webhook_url),
                    json=payload,
                    timeout=10
                )
            
            if response.status_code in [200, 204]:
                logger.info("Discord webhook sent successfully")
                return True
            else:
                logger.error(f"Discord webhook failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Discord webhook: {e}")
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

    def send_milestone_notification(self, digs, clicks, user_id=None, include_screenshot=False, money_value=None, item_counts=None):
        embed = {
            "title": "🎯 Milestone Reached!",
            "color": 0x00FF00,
            "fields": [
                {
                    "name": "⛏️ Digs",
                    "value": f"{digs:,}",
                    "inline": True
                },
                {
                    "name": "🖱️ Clicks", 
                    "value": f"{clicks:,}",
                    "inline": True
                }
            ],
            "timestamp": self._get_timestamp(),
            "footer": {
                "text": "Dig Tool"
            }
        }
        
        if money_value:
            embed["fields"].append({
                "name": "💰 Current Money",
                "value": money_value,
                "inline": True
            })
        
        if item_counts:
            items_found = []
            # Only include scarce and above rarities (exclude junk, common, unusual)
            for rarity, count in item_counts.items():
                if count > 0 and rarity.lower() in ['scarce', 'legendary', 'mythical', 'divine', 'prismatic']:
                    items_found.append(f"{count} {rarity.title()}")
            
            if items_found:
                embed["fields"].append({
                    "name": "Rare Items Found",
                    "value": ", ".join(items_found),
                    "inline": False
                })
            else:
                embed["fields"].append({
                    "name": "Rare Items Found",
                    "value": "No rare items found",
                    "inline": False
                })
        
        if include_screenshot:
            embed["image"] = {
                "url": "attachment://screenshot.png"
            }
            
        payload: dict = {
            "embeds": [embed]
        }
        
        if user_id:
            payload["content"] = f"<@{user_id}>"
            
        return self._send_webhook_request(payload, include_screenshot)


    def send_error_notification(self, error_message, user_id=None):
        message = f"⚠️ Error occurred: {error_message}"
        return self.send_notification(message, user_id, 0xFF9900)

    def test_webhook(self, user_id=None, include_screenshot=False):
        return self.send_notification("🧪 Test notification - Discord integration is working!", user_id, 0x9900ff, include_screenshot)

    def send_item_notification(self, rarity, user_id=None, include_screenshot=False, item_area=None):
        rarity_colors = {
            'legendary': 0xFF8C00,
            'mythical': 0xFF1493,
            'divine': 0x9932CC,
            'prismatic': 0x00FFFF,
            'scarce': 0x0080FF,
            'unusual': 0x32CD32,
            'common': 0x808080,
            'junk': 0x8B4513
        }
        
        color = rarity_colors.get(rarity.lower(), 0x00FF00)
        message = f"🎉 You dug up a {rarity} item!"
        
        # For item notifications, use cropped screenshot if area is provided
        if include_screenshot and item_area:
            return self._send_item_notification_with_cropped_screenshot(message, user_id, color, item_area)
        else:
            return self.send_notification(message, user_id, color, include_screenshot)
    
    def _send_item_notification_with_cropped_screenshot(self, message, user_id, color, item_area):
        if not self.webhook_url:
            logger.warning("Discord webhook URL not set!")
            return False
        
        buffer = None
        try:
            # Capture only the item area
            x, y, width, height = item_area
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            buffer.seek(0)
        except Exception as e:
            logger.error(f"Error capturing item area screenshot: {e}")
            # Fallback to regular notification without screenshot
            return self.send_notification(message, user_id, color, False)

        try:
            content = f"<@{user_id}>" if user_id else ""
            embed = {
                "title": "Dig Tool Notification",
                "description": message,
                "color": color,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
                "image": {
                    "url": "attachment://screenshot.png"
                }
            }

            payload = {
                "content": content,
                "embeds": [embed]
            }

            files = {
                "payload_json": (None, json.dumps(payload), "application/json"),
                "file": ("screenshot.png", buffer, "image/png")
            }
            
            response = requests.post(
                str(self.webhook_url),
                files=files,
                timeout=10
            )

            if response.status_code == 204 or response.status_code == 200:
                logger.info("Discord item notification with cropped screenshot sent successfully")
                return True
            else:
                logger.error(f"Discord item notification failed: {response.status_code}")
                return False
              
        except Exception as e:
            logger.error(f"Error sending Discord item notification: {e}")
            return False
        finally:
            if buffer:
                try:
                    buffer.close()
                except:
                    pass


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
            
            if not dig_tool_instance.money_ocr.initialized:
                logger.info("Auto-initializing OCR for milestone notifications")
                if dig_tool_instance.money_ocr.initialize_ocr():
                    logger.info("OCR initialized successfully")
                else:
                    logger.warning("OCR initialization failed")
            
            if not dig_tool_instance.money_ocr.money_area:
                logger.info("Money area not set, prompting user to select area")
                dig_tool_instance.update_status("Select money area for Discord notifications...")
                
                def select_area_and_continue():
                    try:
                        if dig_tool_instance.money_ocr.select_money_area():
                            logger.info("Money area selected successfully")
                            dig_tool_instance.update_status("Money area selected")
                            _send_milestone_with_money(dig_tool_instance, webhook_url, user_id, include_screenshot)
                        else:
                            logger.warning("Money area selection cancelled")
                            dig_tool_instance.update_status("Money area not selected, sending milestone without money value")
                            _send_milestone_with_money(dig_tool_instance, webhook_url, user_id, include_screenshot, skip_ocr=True)
                    except Exception as e:
                        logger.error(f"Error in area selection: {e}")
                        _send_milestone_with_money(dig_tool_instance, webhook_url, user_id, include_screenshot, skip_ocr=True)
                
                threading.Thread(target=select_area_and_continue, daemon=True).start()
            else:
                _send_milestone_with_money(dig_tool_instance, webhook_url, user_id, include_screenshot)
            
            dig_tool_instance.last_milestone_notification = dig_tool_instance.dig_count

    except Exception as e:
        logger.error(f"Error in check_milestone_notifications: {e}")
        dig_tool_instance.update_status(f"Milestone notification error: {e}")


def _send_milestone_with_money(dig_tool_instance, webhook_url, user_id, include_screenshot, skip_ocr=False):
    dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
    
    def send_milestone():
        try:
            money_value = None
            
            if not skip_ocr and dig_tool_instance.money_ocr.initialized and dig_tool_instance.money_ocr.money_area:
                try:
                    import time
                    time.sleep(0.2)
                    logger.info("Reading money value for milestone notification")
                    money_value = dig_tool_instance.money_ocr.read_money_value()
                    if money_value:
                        logger.info(f"Money value detected: {money_value}")
                    else:
                        logger.warning("No money value detected")
                except Exception as e:
                    logger.error(f"Error reading money value: {e}")
            
            success = dig_tool_instance.discord_notifier.send_milestone_notification(
                dig_tool_instance.dig_count,
                dig_tool_instance.click_count,
                user_id if user_id else None,
                include_screenshot,
                money_value,
                dig_tool_instance.item_counts_since_startup.copy()
            )
            if success:
                logger.info(f"Milestone notification sent successfully for {dig_tool_instance.dig_count} digs")
                # Note: Item counts no longer reset after milestone - only reset when bot stops/starts
            else:
                logger.error(f"Failed to send milestone notification for {dig_tool_instance.dig_count} digs")
        except Exception as e:
            logger.error(f"Error in milestone notification thread: {e}")
    
    threading.Thread(target=send_milestone, daemon=True).start()


def send_startup_notification(dig_tool_instance):
    try:
        import tkinter as tk
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


def check_item_notifications(dig_tool_instance):
    try:
        import tkinter as tk
        webhook_url = dig_tool_instance.param_vars.get('webhook_url', tk.StringVar()).get()
        include_screenshot = dig_tool_instance.param_vars.get('include_screenshot_in_discord', tk.BooleanVar()).get()
        user_id = dig_tool_instance.param_vars.get('user_id', tk.StringVar()).get()

        if not webhook_url:
            logger.debug("Item notification skipped: No webhook URL set")
            return

        if not hasattr(dig_tool_instance, 'item_ocr'):
            from utils.ocr_integration import ItemOCR
            dig_tool_instance.item_ocr = ItemOCR()

        if not dig_tool_instance.item_ocr.initialized:
            if dig_tool_instance.item_ocr.initialize_ocr():
                logger.debug("Item OCR initialized successfully")
            else:
                logger.debug("Item OCR initialization failed")
                return

        if not dig_tool_instance.item_ocr.item_area:
            logger.info("Item area not set, prompting user to select area")
            dig_tool_instance.update_status("Select item area for Discord notifications...")
            
            def select_area_and_continue():
                try:
                    if dig_tool_instance.item_ocr.select_item_area():
                        logger.info("Item area selected successfully")
                        dig_tool_instance.update_status("Item area selected")
                        _check_item_text(dig_tool_instance, webhook_url, user_id, include_screenshot)
                    else:
                        logger.warning("Item area selection cancelled")
                        dig_tool_instance.update_status("Item area not selected")
                except Exception as e:
                    logger.error(f"Error in item area selection: {e}")
            
            threading.Thread(target=select_area_and_continue, daemon=True).start()
        else:
            _check_item_text(dig_tool_instance, webhook_url, user_id, include_screenshot)

    except Exception as e:
        logger.error(f"Error in check_item_notifications: {e}")


def _check_item_text(dig_tool_instance, webhook_url, user_id, include_screenshot):
    dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
    
    def check_item():
        try:
            import time
            time.sleep(0.2)
            logger.info("Reading item text for notification check")
            item_text = dig_tool_instance.item_ocr.read_item_text()
            
            if item_text:
                rarity = dig_tool_instance.item_ocr.extract_rarity(item_text)
                
                if rarity:
                    dig_tool_instance.count_item_rarity(rarity)
                    
                    if rarity.lower() in ['legendary', 'mythical', 'divine', 'prismatic', 'scarce']:
                        logger.info(f"Rare item detected: {rarity}")
                        success = dig_tool_instance.discord_notifier.send_item_notification(
                            rarity,
                            user_id if user_id else None,
                            include_screenshot,
                            dig_tool_instance.item_ocr.item_area if include_screenshot else None
                        )
                        if success:
                            logger.info(f"Item notification sent successfully for {rarity} item")
                            dig_tool_instance.update_status(f"Notified: {rarity} item found!")
                        else:
                            logger.error(f"Failed to send item notification for {rarity} item")
                    else:
                        logger.debug(f"Common item detected: {rarity}")
                else:
                    logger.debug("Item text detected but no rarity found")
            else:
                logger.debug("No item text detected")
                
        except Exception as e:
            logger.error(f"Error in item check thread: {e}")
    
    threading.Thread(target=check_item, daemon=True).start()


def send_shutdown_notification(dig_tool_instance):
    try:
        import tkinter as tk
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
