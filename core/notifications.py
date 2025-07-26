import requests
import time
import io
import json
import threading
from PIL import ImageGrab
from utils.debug_logger import logger
from utils.config_management import get_param


class DiscordNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url
        self.stats_message_id = None
        self.guild_id = None
        self.channel_id = None
        self.previous_stats = {
            'digs': 0,
            'clicks': 0,
            'money_value': None,
            'item_counts': {}
        }

    def set_webhook_url(self, webhook_url):
        self.webhook_url = webhook_url

    def set_server_id(self, server_id):
        self.guild_id = server_id
        if not server_id:
            logger.warning("No server ID provided - message links will be disabled")

    def _extract_channel_id_from_response(self, response_data):
        if 'channel_id' in response_data:
            self.channel_id = response_data.get('channel_id')

    def _get_stats_message_link(self):
        if not self.guild_id:
            logger.warning("Server ID not set - message links disabled. Set Discord Server ID in settings to enable message links.")
            return None
            
        if self.guild_id and self.channel_id and self.stats_message_id:
            return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.stats_message_id}"
        else:
            return None

    def _capture_screenshot(self, screenshot_area=None):
        try:
            if screenshot_area:
                x, y, width, height = screenshot_area
                screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            else:
                screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            buffer.seek(0)
            return buffer
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return None

    def _send_webhook_request(self, payload, include_screenshot=False, screenshot_area=None):
        if not self.webhook_url:
            logger.warning("Discord webhook URL not set!")
            return False

        buffer = None
        if include_screenshot:
            buffer = self._capture_screenshot(screenshot_area)
            if not buffer:
                include_screenshot = False

        try:
            if include_screenshot and buffer:
                files = {
                    "payload_json": (None, json.dumps(payload), "application/json"),
                    "file": ("screenshot.png", buffer, "image/png")
                }
                response = requests.post(str(self.webhook_url), files=files, timeout=10)
            else:
                response = requests.post(str(self.webhook_url), json=payload, headers={'Content-Type': 'application/json'}, timeout=10)

            if response.status_code in [200, 204]:
                logger.info("Discord webhook sent successfully")
                return response
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

    def send_notification(self, message, user_id=None, color=0x00ff00, include_screenshot=False, screenshot_area=None):
        content = f"<@{user_id}>" if user_id else ""
        embed = {
            "title": "Dig Tool Notification",
            "description": message,
            "color": color,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "image": {"url": "attachment://screenshot.png"} if include_screenshot else None
        }
        payload = {"content": content, "embeds": [embed]}
        result = self._send_webhook_request(payload, include_screenshot, screenshot_area)
        return bool(result)

    def send_initial_stats_message(self, user_id=None):
        embed = {
            "title": "📊 Dig Tool Status",
            "color": 0x5865F2,
            "fields": [
                {"name": "⛏️ Digs", "value": "0", "inline": True},
                {"name": "🖱️ Clicks", "value": "0", "inline": True},
                {"name": "💰 Current Money", "value": "Not detected", "inline": True},
                {"name": "📦 Items Found", "value": "No items found yet", "inline": False}
            ],
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "footer": {"text": "Live Stats"}
        }

        content = f"<@{user_id}>" if user_id else ""
        payload = {"content": content, "embeds": [embed]}

        try:
            webhook_url_with_wait = f"{str(self.webhook_url)}?wait=true"
            response = requests.post(webhook_url_with_wait, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)

            if response.status_code in [200, 204]:
                if response.text and response.text.strip():
                    try:
                        response_data = response.json()
                        self.stats_message_id = response_data.get('id')
                        self._extract_channel_id_from_response(response_data)
                        
                        logger.info(f"Initial stats message sent, ID: {self.stats_message_id}")
                        
                        stats_link = self._get_stats_message_link()
                        if stats_link:
                            logger.info(f"Stats message link ready: {stats_link}")
                        else:
                            if not self.guild_id:
                                logger.info("Set Discord Server ID in settings to enable message links")
                            else:
                                logger.warning("Could not generate stats message link")
                        
                        return True
                    except Exception as e:
                        logger.warning(f"Could not parse response JSON: {e}")
                        logger.info("Initial stats message sent successfully (no message ID)")
                        return True
                else:
                    logger.info("Initial stats message sent successfully (no message ID)")
                    return True
            else:
                logger.error(f"Failed to send initial stats message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending initial stats message: {e}")
            return False

    def update_stats_message(self, digs, clicks=0, money_value=None, item_counts=None, dig_tool_instance=None):
        if not self.webhook_url or not self.stats_message_id:
            logger.error(f"Cannot update stats: webhook_url={bool(self.webhook_url)}, message_id={bool(self.stats_message_id)}")
            return False

        dig_increase = digs - self.previous_stats['digs']
        click_increase = clicks - self.previous_stats['clicks']
        
        embed = {
            "title": "📊 Dig Tool Status",
            "color": 0x5865F2,
            "fields": [],
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "footer": {"text": "Live Stats"}
        }

        digs_value = f"{digs:,} (+{dig_increase:,})" if dig_increase > 0 else f"{digs:,}"
        clicks_value = f"{clicks:,} (+{click_increase:,})" if click_increase > 0 else f"{clicks:,}"
        
        embed["fields"].extend([
            {"name": "⛏️ Digs", "value": digs_value, "inline": True},
            {"name": "�️ Clicks", "value": clicks_value, "inline": True},
            {"name": "💰 Current Money", "value": money_value or "Not detected", "inline": True}
        ])

        if item_counts:
            items_found = []
            previous_item_counts = self.previous_stats.get('item_counts', {})
            
            for rarity, count in item_counts.items():
                if count > 0:
                    previous_count = previous_item_counts.get(rarity, 0)
                    increase = count - previous_count
                    if increase > 0:
                        items_found.append(f"{count} {rarity.title()} (+{increase})")
                    else:
                        items_found.append(f"{count} {rarity.title()}")
            
            items_text = ", ".join(items_found) if items_found else "No items found yet"
            embed["fields"].append({"name": "📦 Items Found", "value": items_text, "inline": False})
        else:
            embed["fields"].append({"name": "📦 Items Found", "value": "No items found yet", "inline": False})

        payload = {"embeds": [embed]}

        try:
            webhook_parts = str(self.webhook_url).split('/')
            webhook_id = webhook_parts[-2]
            webhook_token = webhook_parts[-1]
            
            edit_url = f"https://discord.com/api/webhooks/{webhook_id}/{webhook_token}/messages/{self.stats_message_id}"
            
            response = requests.patch(edit_url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)

            if response.status_code in [200, 204]:
                logger.info("Stats message updated successfully")
                self.previous_stats = {
                    'digs': digs,
                    'clicks': clicks,
                    'money_value': money_value,
                    'item_counts': item_counts.copy() if item_counts else {}
                }
                return True
            else:
                logger.error(f"Failed to update stats message: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Exception during stats update: {e}")
            return False

    def send_milestone_notification(self, digs, clicks, user_id=None, include_screenshot=False, money_value=None, item_counts=None, dig_tool_instance=None):
        if not self.webhook_url:
            logger.warning("Discord webhook URL not set!")
            return False

        dig_increase = digs - self.previous_stats['digs']
        click_increase = clicks - self.previous_stats['clicks']

        embed = {
            "title": "🎉 Milestone Reached",
            "color": 0x5865F2,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "footer": {"text": "Dig Tool"}
        }

        description_parts = []
        
        if dig_increase > 0 or click_increase > 0:
            increments = []
            if dig_increase > 0:
                increments.append(f"⛏️ +{dig_increase:,} digs")
            if click_increase > 0:
                increments.append(f"🖱️ +{click_increase:,} clicks")
            
            if increments:
                description_parts.append(f"*{' • '.join(increments)} since last milestone*")

        if include_screenshot:
            embed["image"] = {"url": "attachment://screenshot.png"}
        
        stats_link = self._get_stats_message_link()
        if stats_link:
            description_parts.append(f"[📊 View Live Stats]({stats_link})")
        
        if description_parts:
            embed["description"] = "\n\n".join(description_parts)

        content = f"<@{user_id}>" if user_id else ""
        payload = {"content": content, "embeds": [embed]}

        return self._send_webhook_request(payload, include_screenshot)    
    def send_error_notification(self, error_message, user_id=None):
        return self.send_notification(f"⚠️ Error occurred: {error_message}", user_id, 0xFF9900)

    def test_webhook(self, user_id=None, include_screenshot=False):
        embed = {
            "title": "🧪 Test Notification",
            "description": "Discord integration is working!",
            "color": 0x57F287,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "footer": {"text": "Dig Tool"}
        }

        stats_link = self._get_stats_message_link()
        if stats_link:
            embed["description"] += f"\n[📊 View Live Stats]({stats_link})"

        if include_screenshot:
            embed["image"] = {"url": "attachment://screenshot.png"}

        content = f"<@{user_id}>" if user_id else ""
        payload = {"content": content, "embeds": [embed]}

        result = self._send_webhook_request(payload, include_screenshot)
        return bool(result)

    def send_startup_notification(self, user_id=None):
        startup_success = self.send_notification("🟢 Bot started and ready!", user_id, 0x57F287)
        stats_success = self.send_initial_stats_message(user_id)
        return startup_success and stats_success

    def send_shutdown_notification(self, user_id=None):
        return self.send_notification("🔴 Bot stopped.", user_id, 0xED4245)

    def send_item_notification(self, rarity, user_id=None, include_screenshot=False, full_item_text=None, item_area=None):
        rarity_colors = {
            'scarce': 0xBB68F3,
            'legendary': 0xFF8C00,
            'mythical': 0xFF1493,
            'divine': 0xFF0000,
            'prismatic': 0xF34545,
        }
        
        color = rarity_colors.get(rarity.lower(), 0x00FF00)
        message = f"You dug up a {rarity} item!" if full_item_text and full_item_text.strip() else f"You dug up a {rarity} item!"
        
        embed = {
            "title": "💎 Item Found",
            "description": message,
            "color": color,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime()),
            "footer": {"text": "Dig Tool"}
        }

        if include_screenshot:
            embed["image"] = {"url": "attachment://screenshot.png"}

        stats_link = self._get_stats_message_link()
        if stats_link:
            embed["description"] += f"\n\n[📊 View Live Stats]({stats_link})"

        content = f"<@{user_id}>" if user_id else ""
        payload = {"content": content, "embeds": [embed]}

        result = self._send_webhook_request(payload, include_screenshot, item_area)
        return bool(result)


def test_discord_ping(dig_tool_instance):
    try:
        import tkinter as tk
        webhook_url = dig_tool_instance.param_vars.get('webhook_url', tk.StringVar()).get()
        server_id = dig_tool_instance.param_vars.get('server_id', tk.StringVar()).get()
        include_screenshot = dig_tool_instance.param_vars.get('include_screenshot_in_discord', tk.BooleanVar()).get()
        user_id = dig_tool_instance.param_vars.get('user_id', tk.StringVar()).get()

        if not webhook_url:
            dig_tool_instance.update_status("Webhook URL not set!")
            return

        dig_tool_instance.update_status("Testing Discord ping...")
        dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
        if server_id:
            dig_tool_instance.discord_notifier.set_server_id(server_id)

        def test_and_report():
            try:
                success = dig_tool_instance.discord_notifier.test_webhook(user_id if user_id else None, include_screenshot)
                status = "Discord ping test completed successfully!" if success else "Discord ping test failed!"
                dig_tool_instance.update_status(status)
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
        server_id = dig_tool_instance.param_vars.get('server_id', tk.StringVar()).get()
        include_screenshot = dig_tool_instance.param_vars.get('include_screenshot_in_discord', tk.BooleanVar()).get()
        user_id = dig_tool_instance.param_vars.get('user_id', tk.StringVar()).get()
        milestone_interval = dig_tool_instance.param_vars.get('milestone_interval', tk.IntVar()).get()
        enable_money_detection = dig_tool_instance.param_vars.get('enable_money_detection', tk.BooleanVar()).get()

        if not webhook_url or milestone_interval <= 0:
            return

        if (dig_tool_instance.dig_count > 0 and 
            dig_tool_instance.dig_count % milestone_interval == 0 and 
            dig_tool_instance.dig_count != dig_tool_instance.last_milestone_notification):
            
            if enable_money_detection:
                if not dig_tool_instance.money_ocr.initialized:
                    if not dig_tool_instance.money_ocr.initialize_ocr():
                        logger.warning("OCR initialization failed")
                
                if not dig_tool_instance.money_ocr.money_area:
                    dig_tool_instance.update_status("Select money area for Discord notifications...")
                    
                    def select_area_and_continue():
                        try:
                            if dig_tool_instance.money_ocr.select_money_area():
                                dig_tool_instance.update_status("Money area selected")
                                _send_milestone_with_money(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot)
                            else:
                                dig_tool_instance.update_status("Money area not selected, sending milestone without money value")
                                _send_milestone_with_money(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot, skip_ocr=True)
                        except Exception as e:
                            logger.error(f"Error in area selection: {e}")
                            _send_milestone_with_money(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot, skip_ocr=True)
                    
                    threading.Thread(target=select_area_and_continue, daemon=True).start()
                else:
                    _send_milestone_with_money(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot)
            else:
                _send_milestone_with_money(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot, skip_ocr=True)
            
            if hasattr(dig_tool_instance, 'discord_notifier') and dig_tool_instance.discord_notifier.stats_message_id:
                try:
                    money_value = None
                    if enable_money_detection and hasattr(dig_tool_instance, 'money_ocr') and dig_tool_instance.money_ocr:
                        try:
                            money_value = dig_tool_instance.money_ocr.read_money_value()
                        except Exception as e:
                            logger.debug(f"Money OCR failed: {e}")
                    
                    item_counts = None
                    if hasattr(dig_tool_instance, 'item_counts_since_startup'):
                        item_counts = dig_tool_instance.item_counts_since_startup.copy()
                    
                    success = dig_tool_instance.discord_notifier.update_stats_message(
                        digs=dig_tool_instance.dig_count,
                        clicks=getattr(dig_tool_instance, 'click_count', 0),
                        money_value=money_value,
                        item_counts=item_counts,
                        dig_tool_instance=dig_tool_instance
                    )
                    
                except Exception as e:
                    logger.error(f"Error updating Discord stats: {e}")
            
            dig_tool_instance.last_milestone_notification = dig_tool_instance.dig_count

    except Exception as e:
        logger.error(f"Error in check_milestone_notifications: {e}")
        dig_tool_instance.update_status(f"Milestone notification error: {e}")


def _send_milestone_with_money(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot, skip_ocr=False):
    dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
    if server_id:
        dig_tool_instance.discord_notifier.set_server_id(server_id)
    
    def send_milestone():
        try:
            money_value = None
            if not skip_ocr and dig_tool_instance.money_ocr.initialized and dig_tool_instance.money_ocr.money_area:
                try:
                    money_value = dig_tool_instance.money_ocr.read_money_value()
                except Exception as e:
                    logger.error(f"Error reading money value: {e}")
            
            success = dig_tool_instance.discord_notifier.send_milestone_notification(
                digs=dig_tool_instance.dig_count,
                clicks=0,
                user_id=user_id if user_id else None,
                include_screenshot=include_screenshot,
                money_value=money_value,
                item_counts=dig_tool_instance.item_counts_since_startup.copy(),
                dig_tool_instance=dig_tool_instance
            )
            if not success:
                logger.error(f"Failed to send milestone notification for {dig_tool_instance.dig_count} digs")
        except Exception as e:
            logger.error(f"Error in milestone notification thread: {e}")
    
    threading.Thread(target=send_milestone, daemon=True).start()


def send_startup_notification(dig_tool_instance):
    try:
        import tkinter as tk
        webhook_url = dig_tool_instance.param_vars.get("webhook_url", tk.StringVar()).get()
        server_id = dig_tool_instance.param_vars.get("server_id", tk.StringVar()).get()
        user_id = dig_tool_instance.param_vars.get("user_id", tk.StringVar()).get()
        if webhook_url:
            dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
            if server_id:
                dig_tool_instance.discord_notifier.set_server_id(server_id)
            
            def send_startup():
                try:
                    success = dig_tool_instance.discord_notifier.send_startup_notification(user_id)
                    if not success:
                        logger.error("Failed to send startup notification")
                except Exception as e:
                    logger.error(f"Error in startup notification thread: {e}")
            
            threading.Thread(target=send_startup, daemon=True).start()
    except Exception as e:
        logger.error(f"Error in send_startup_notification: {e}")


def check_item_notifications(dig_tool_instance):
    try:
        import tkinter as tk
        webhook_url = dig_tool_instance.param_vars.get('webhook_url', tk.StringVar()).get()
        server_id = dig_tool_instance.param_vars.get('server_id', tk.StringVar()).get()
        include_screenshot = dig_tool_instance.param_vars.get('include_screenshot_in_discord', tk.BooleanVar()).get()
        user_id = dig_tool_instance.param_vars.get('user_id', tk.StringVar()).get()

        if not webhook_url:
            return

        if not hasattr(dig_tool_instance, 'item_ocr'):
            from core.ocr import ItemOCR
            dig_tool_instance.item_ocr = ItemOCR()

        if not dig_tool_instance.item_ocr.initialized:
            if not dig_tool_instance.item_ocr.initialize_ocr():
                return

        if not dig_tool_instance.item_ocr.item_area:
            dig_tool_instance.update_status("Select item area for Discord notifications...")
            
            def select_area_and_continue():
                try:
                    if dig_tool_instance.item_ocr.select_item_area():
                        dig_tool_instance.update_status("Item area selected")
                        _check_item_text(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot)
                    else:
                        dig_tool_instance.update_status("Item area not selected")
                except Exception as e:
                    logger.error(f"Error in item area selection: {e}")
            
            threading.Thread(target=select_area_and_continue, daemon=True).start()
        else:
            _check_item_text(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot)

    except Exception as e:
        logger.error(f"Error in check_item_notifications: {e}")


def _check_item_text(dig_tool_instance, webhook_url, server_id, user_id, include_screenshot):
    dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
    if server_id:
        dig_tool_instance.discord_notifier.set_server_id(server_id)
    
    def check_item():
        try:            
            item_text = dig_tool_instance.item_ocr.read_item_text()
            
            if item_text:
                rarity = dig_tool_instance.item_ocr.extract_rarity(item_text)
                
                if rarity:
                    dig_tool_instance.count_item_rarity(rarity)
                    
                    notification_rarities = ['scarce', 'legendary', 'mythical', 'divine', 'prismatic']
                    try:
                        config_rarities = get_param(dig_tool_instance, "notification_rarities")
                        if config_rarities:
                            if isinstance(config_rarities, str):
                                notification_rarities = json.loads(config_rarities) if config_rarities.strip() else notification_rarities
                            elif isinstance(config_rarities, list):
                                notification_rarities = config_rarities
                    except Exception as e:
                        logger.warning(f"Error getting notification rarities from config: {e}")
                    
                    if rarity.lower() in [r.lower() for r in notification_rarities]:
                        item_area = dig_tool_instance.item_ocr.item_area if hasattr(dig_tool_instance.item_ocr, 'item_area') else None
                        success = dig_tool_instance.discord_notifier.send_item_notification(
                            rarity, user_id if user_id else None, include_screenshot, item_text, item_area)
                        if success:
                            dig_tool_instance.update_status(f"Notified: {item_text}")
                        else:
                            logger.error(f"Failed to send item notification for {rarity} item")
                
        except Exception as e:
            logger.error(f"Error in item check thread: {e}")
    
    threading.Thread(target=check_item, daemon=True).start()


def send_shutdown_notification(dig_tool_instance):
    try:
        import tkinter as tk
        webhook_url = dig_tool_instance.param_vars.get("webhook_url", tk.StringVar()).get()
        server_id = dig_tool_instance.param_vars.get("server_id", tk.StringVar()).get()
        user_id = dig_tool_instance.param_vars.get("user_id", tk.StringVar()).get()
        if webhook_url:
            dig_tool_instance.discord_notifier.set_webhook_url(webhook_url)
            if server_id:
                dig_tool_instance.discord_notifier.set_server_id(server_id)
            
            def send_shutdown():
                try:
                    success = dig_tool_instance.discord_notifier.send_shutdown_notification(user_id)
                    if not success:
                        logger.error("Failed to send shutdown notification")
                except Exception as e:
                    logger.error(f"Error in shutdown notification thread: {e}")
            
            threading.Thread(target=send_shutdown, daemon=True).start()
    except Exception as e:
        logger.error(f"Error in send_shutdown_notification: {e}")
