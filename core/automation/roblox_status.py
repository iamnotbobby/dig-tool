import os
import re
import time
import threading
import webbrowser
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils.debug_logger import logger
from utils.system_utils import find_and_focus_roblox_window


class RobloxLogFileHandler(FileSystemEventHandler):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor

    def on_modified(self, event):
        if not event.is_directory and event.src_path == str(self.monitor.current_log_file):
            self.monitor.process_log_file()


class RobloxStatusMonitor:
    def __init__(self, dig_tool_instance=None):
        self._stop_event = threading.Event()
        self.dig_tool = dig_tool_instance
        self.current_log_file = None
        self.current_file_position = 0
        self.log_observer = None
        self.observer_handler = RobloxLogFileHandler(self)
        self.is_joining = self.is_playing = self.is_disconnected = self.is_game_left = self.is_roblox_closed = False
        self.disconnect_reason = "N/A"
        self.file_patterns = ["*_Player_*.log"]
        self.joining_keyword = "[FLog::Output] ! Joining game"
        self.joined_keyword = "[FLog::Network] serverId:"
        self.disconnect_keyword = "[FLog::Network] Sending disconnect with reason"
        self.leaving_keyword = "[DFLog::MegaReplicatorLogDisconnectCleanUpLog] Destroying MegaReplicator."
        self.closing_keyword = "finished destroying luaApp"
        self.disconnect_regex = r"Sending disconnect with reason:\s*(\d+)"
        self.log_path = Path.home() / "AppData" / "Local" / "Roblox" / "logs"
        self._last_notification_time = {}
        self._notification_cooldown = 10
        self._notification_lock = threading.Lock()
        self._automation_was_running = False
        self._last_processed_joined_time = 0
        self.last_rejoin_attempt = None

    def reset_status(self, clear_notifications=True, preserve_automation_state=False):
        self.is_joining = self.is_playing = self.is_disconnected = self.is_game_left = self.is_roblox_closed = False
        self.disconnect_reason = "N/A"
        if not preserve_automation_state:
            self._automation_was_running = False
            self._last_processed_joined_time = 0
        if clear_notifications:
            self._last_notification_time.clear()

    def send_discord_notification(self, message, color=0xFF6B35, include_user=True):
        if not self.dig_tool or not hasattr(self.dig_tool, "discord_notifier"):
            return
        with self._notification_lock:
            try:
                from utils.config_management import get_param
                if not get_param(self.dig_tool, "auto_rejoin_discord_notifications"):
                    return
                current_time = time.time()
                message_key = ("disconnect" if any(x in message for x in ["Disconnected", "Kicked", "Timeout", "Banned"]) 
                              else "rejoining" if "Auto-rejoining" in message 
                              else "rejoin_success" if "Auto-rejoin successful" in message 
                              else "rejoin_failed" if "Auto-rejoin failed" in message 
                              else message.split(":")[0] if ":" in message else message)
                if (message_key in self._last_notification_time and 
                    current_time - self._last_notification_time[message_key] < self._notification_cooldown):
                    return
                self._last_notification_time[message_key] = current_time
                webhook_url = get_param(self.dig_tool, "webhook_url")
                if webhook_url and webhook_url.strip():
                    self.dig_tool.discord_notifier.set_webhook_url(webhook_url)
                    user_id = get_param(self.dig_tool, "user_id") if include_user else None
                    self.dig_tool.discord_notifier.send_notification(
                        message=message, user_id=user_id if user_id and user_id.strip() else None, color=color)
            except Exception as e:
                logger.debug(f"Error sending Discord notification: {e}")

    def get_latest_log_file(self):
        if not self.log_path.exists():
            return None
        latest_file, latest_time = None, 0
        for pattern in self.file_patterns:
            for log_file in self.log_path.glob(pattern):
                if log_file.is_file() and (file_time := log_file.stat().st_mtime) > latest_time:
                    latest_time, latest_file = file_time, log_file
        return latest_file

    def process_log_file(self):
        from utils.config_management import get_param
        if not self.current_log_file or not get_param(self.dig_tool, "auto_rejoin_enabled"):
            return
        try:
            with open(str(self.current_log_file), "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self.current_file_position)
                new_lines = [line.strip() for line in f]
                self.current_file_position = f.tell()
                for line in new_lines:
                    self.parse_log_line(line)
        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.debug(f"Error reading Roblox log file: {e}")

    def parse_log_line(self, line):
        if self.joining_keyword in line:
            logger.info("Roblox: Game joining detected")
            self.reset_status(preserve_automation_state=True)
            self.is_joining = True
        elif self.joined_keyword in line:
            current_time = time.time()
            if current_time - self._last_processed_joined_time < 5:
                return
            self._last_processed_joined_time = current_time
            logger.info("Roblox: Game joined successfully")
            self.reset_status(preserve_automation_state=True)
            self.is_playing = True
            if hasattr(self.dig_tool, "is_auto_rejoining"):
                self.dig_tool.is_auto_rejoining = False
                if hasattr(self.dig_tool, "update_status"):
                    self.dig_tool.update_status("Game joined successfully")
            if hasattr(self, "_recently_rejoined") and self._recently_rejoined:
                self.send_discord_notification("✅ **Successfully rejoined**: Now connected to server", color=0x2ED573)
                self._recently_rejoined = False
                if hasattr(self.dig_tool, 'rejoiner') and hasattr(self.dig_tool.rejoiner, '_current_attempt_start'):
                    self.dig_tool.rejoiner._current_attempt_start = None
                self._resume_automation_after_rejoin()
        elif self.disconnect_keyword in line:
            reason = (match := re.search(self.disconnect_regex, line)) and match.group(1) or "N/A"
            logger.info(f"Roblox: Player disconnected (reason: {reason})")
            self.reset_status(clear_notifications=False)
            self.is_disconnected = True
            self.disconnect_reason = reason
            self._pause_automation_on_disconnect()
            disconnect_messages = {"17": "🔌 **Disconnected**: Lost connection to server", "267": "⚠️ **Kicked**: You were kicked from the server", 
                                   "279": "⏰ **Timeout**: Connection timed out", "529": "🚫 **Banned**: You have been banned from this server", 
                                   "773": "🔄 **Teleport**: Server is teleporting players"}
            self.send_discord_notification(disconnect_messages.get(reason, f"❌ **Disconnected**: Reason code {reason}"), color=0xFF4757)
        elif self.leaving_keyword in line:
            logger.info("Roblox: Player left game")
            self.reset_status(clear_notifications=False)
            self.is_game_left = True
            self._pause_automation_on_disconnect()
        elif self.closing_keyword in line:
            logger.info("Roblox: Application closed")
            self.reset_status(clear_notifications=False)
            self.is_roblox_closed = True
            self._pause_automation_on_disconnect()

    def start_file_watcher(self):
        if not self.log_path.exists():
            os.makedirs(str(self.log_path), exist_ok=True)
        self.log_observer = Observer()
        self.log_observer.schedule(self.observer_handler, path=self.log_path, recursive=False)
        self.log_observer.start()

    def stop_file_watcher(self):
        if self.log_observer and self.log_observer.should_keep_running():
            self.log_observer.stop()
            self.log_observer.join()
            self.log_observer = None

    def monitor_log_files(self):
        from utils.config_management import get_param
        check_interval = 1.0
        while not self._stop_event.is_set():
            if not get_param(self.dig_tool, "auto_rejoin_enabled"):
                time.sleep(check_interval)
                continue
            next_interval = check_interval
            if (latest_file := self.get_latest_log_file()) and str(latest_file) != str(self.current_log_file):
                old_file = self.current_log_file
                self.current_log_file = latest_file
                logger.info(f"Switching to new log file: {self.current_log_file}")
                try:
                    with open(str(self.current_log_file), "r", encoding="utf-8", errors="ignore") as f:
                        if old_file is None:
                            f.seek(0, 2)
                            self.current_file_position = f.tell()
                        else:
                            content = f.read()
                            self.current_file_position = f.tell()
                            lines = content.strip().split('\n')
                            logger.info(f"Processing {len(lines)} lines from new log file")
                            for line in lines:
                                if line.strip():
                                    self.parse_log_line(line.strip())
                except Exception as e:
                    logger.debug(f"Error reading new log file: {e}")
                    try:
                        with open(str(self.current_log_file), "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(0, 0)
                            self.current_file_position = f.tell()
                    except Exception:
                        self.current_file_position = 0
                if old_file:
                    self.reset_status(clear_notifications=False, preserve_automation_state=True)
                next_interval = 0.5
            if hasattr(self, 'last_rejoin_attempt') and self.last_rejoin_attempt:
                time_since_rejoin = time.time() - self.last_rejoin_attempt
                if time_since_rejoin < 30:  
                    next_interval = 0.5
            time.sleep(next_interval)

    def start(self):
        logger.info("Starting Roblox status monitoring...")
        threading.Thread(target=self.monitor_log_files, daemon=True).start()
        self.start_file_watcher()

    def stop(self):
        logger.info("Stopping Roblox status monitoring...")
        self._stop_event.set()
        self.stop_file_watcher()

    def can_rejoin(self):
        return (self.is_disconnected or self.is_game_left or self.is_roblox_closed or not self.is_roblox_running())

    def is_roblox_running(self):
        try:
            import psutil
            return any("RobloxPlayer" in proc.name() for proc in psutil.process_iter() if proc.name())
        except:
            return True

    def _pause_automation_on_disconnect(self):
        if not self.dig_tool:
            return
        try:
            from utils.config_management import get_param
            auto_rejoin_enabled = get_param(self.dig_tool, "auto_rejoin_enabled")
            if hasattr(self.dig_tool, "running") and self.dig_tool.running:
                self._automation_was_running = True
                logger.info("Auto-rejoin: Stopping automation due to disconnect")
                self.dig_tool.running = False
                if hasattr(self.dig_tool, "update_status"):
                    self.dig_tool.update_status("Stopped (Disconnected) - Auto-rejoin monitoring..." if auto_rejoin_enabled else "Stopped (Disconnected)")
                from utils.ui_management import update_main_button_text
                update_main_button_text(self.dig_tool)
            else:
                self._automation_was_running = False
        except Exception as e:
            logger.debug(f"Error stopping automation: {e}")

    def _resume_automation_after_rejoin(self, delay=None):
        if not self.dig_tool:
            return
        from utils.config_management import get_param
        if delay is None:
            delay = get_param(self.dig_tool, "auto_rejoin_restart_delay")
        delay = max(5, int(delay))
        logger.info(f"Auto-rejoin: Will restart automation (previous state: was_running={self._automation_was_running})")
        try:
            def delayed_restart():
                logger.info(f"Auto-rejoin: Waiting {delay} seconds before restarting automation...")
                time.sleep(delay)
                find_and_focus_roblox_window()
                try:
                    logger.info("Auto-rejoin: Re-equipping shovel...")
                    import keyboard
                    keyboard.press_and_release('1')
                    time.sleep(0.5)
                except Exception as e:
                    logger.debug(f"Error re-equipping shovel: {e}")
                logger.info(f"Auto-rejoin: Delay complete, checking restart conditions...")
                if hasattr(self.dig_tool, "running") and not self.dig_tool.running:
                    logger.info("Auto-rejoin: Restarting automation after successful rejoin")
                    automation_manager = getattr(self.dig_tool, "automation_manager", None)
                    if automation_manager and hasattr(automation_manager, "restart_automation"):
                        logger.info("Auto-rejoin: Calling restart_automation method...")
                        automation_manager.restart_automation("Auto-rejoin restart")
                        logger.info("Auto-rejoin: Automation restarted fresh")
                        self._automation_was_running = False
                    else:
                        logger.error("Auto-rejoin: restart_automation method not found!")
                else:
                    logger.warning(f"Auto-rejoin: Cannot restart - tool already running or missing running attribute")
            threading.Thread(target=delayed_restart, daemon=True).start()
        except Exception as e:
            logger.error(f"Error restarting automation: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")


class RobloxRejoiner:
    def __init__(self, dig_tool_instance):
        self.dig_tool = dig_tool_instance
        self.status_monitor = RobloxStatusMonitor(dig_tool_instance)
        self.rejoin_attempts = 0
        self.last_rejoin_time = 0
        self.min_rejoin_interval = 30
        self._rejoin_lock = threading.Lock()
        self._is_rejoining = False
        self._current_attempt_start = None
        self._max_attempts = 5

    def get_server_url(self):
        from utils.config_management import get_param

        server_link = get_param(self.dig_tool, "roblox_server_link")
        if not server_link:
            return None
        if "roblox.com/share?" in server_link:
            return server_link.replace(
                "https://www.roblox.com/share?", "roblox://experiences/start?"
            )
        elif "roblox.com/games/" in server_link:
            if game_id := re.search(r"/games/(\d+)", server_link):
                return f"roblox://experiences/start?placeId={game_id.group(1)}"
        return server_link if server_link.startswith("roblox://") else None

    def launch_roblox(self, url):
        try:
            self.kill_roblox()
            time.sleep(1)
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Failed to launch Roblox: {e}")
            return False

    def kill_roblox(self):
        try:
            import psutil
            for proc in psutil.process_iter():
                if "RobloxPlayer" in proc.name():
                    proc.terminate()
        except:
            pass

    def should_rejoin(self):
        from utils.config_management import get_param
        with self._rejoin_lock:
            return (not self._is_rejoining and get_param(self.dig_tool, "auto_rejoin_enabled") and 
                    get_param(self.dig_tool, "roblox_server_link") and get_param(self.dig_tool, "rejoin_check_interval") > 0 and
                    time.time() - self.last_rejoin_time >= self.min_rejoin_interval and self.status_monitor.can_rejoin() and 
                    self.status_monitor._automation_was_running)

    def attempt_rejoin(self):
        if not self._rejoin_lock.acquire(blocking=False) or self._is_rejoining:
            return False
        try:
            self._is_rejoining = True
            if not (server_url := self.get_server_url()):
                self.status_monitor.send_discord_notification("❌ **Auto-rejoin failed**: No valid server URL configured", color=0xFF4757)
                return False
            if time.time() - self.last_rejoin_time < self.min_rejoin_interval:
                return False
            if self.rejoin_attempts >= self._max_attempts:
                self.status_monitor.send_discord_notification(f"❌ **Auto-rejoin stopped**: Maximum attempts ({self._max_attempts}) reached", color=0xFF4757)
                logger.error(f"Auto-rejoin: Maximum attempts ({self._max_attempts}) reached, stopping")
                return False
            logger.info(f"Auto-rejoin: Attempting to rejoin server...")
            self.last_rejoin_time = time.time()
            self.last_rejoin_attempt = time.time()
            self._current_attempt_start = time.time()
            if hasattr(self.dig_tool, "is_auto_rejoining"):
                self.dig_tool.is_auto_rejoining = True
                if hasattr(self.dig_tool, "update_status"):
                    self.dig_tool.update_status("Auto-rejoining server...")
            self.status_monitor.send_discord_notification("🔄 **Auto-rejoining**: Attempting to rejoin server...", color=0xFFA502, include_user=False)
            if self.launch_roblox(server_url):
                self.rejoin_attempts += 1
                logger.info(f"Auto-rejoin: Roblox launched successfully (attempt #{self.rejoin_attempts})")
                self.status_monitor._recently_rejoined = True
                self.status_monitor.send_discord_notification(f"🔄 **Auto-rejoin successful**: Roblox launched (attempt #{self.rejoin_attempts})", color=0x2ED573, include_user=False)
                self._start_connection_timeout()
                return True
            else:
                self.rejoin_attempts += 1
                self.status_monitor.send_discord_notification(f"❌ **Auto-rejoin failed**: Could not launch Roblox (attempt #{self.rejoin_attempts})", color=0xFF4757)
            return False
        finally:
            self._is_rejoining = False
            if hasattr(self.dig_tool, "is_auto_rejoining"):
                self.dig_tool.is_auto_rejoining = False
                if hasattr(self.dig_tool, "update_status"):
                    self.dig_tool.update_status("Auto-rejoin completed")
            self._rejoin_lock.release()

    def _start_connection_timeout(self):
        def check_connection():
            time.sleep(60)
            if (self._current_attempt_start and hasattr(self.status_monitor, '_recently_rejoined') and self.status_monitor._recently_rejoined):
                logger.warning("Auto-rejoin: No connection confirmation after 60s, retrying...")
                self.status_monitor._recently_rejoined = False
                if self.rejoin_attempts < self._max_attempts:
                    threading.Thread(target=self.attempt_rejoin, daemon=True).start()
        threading.Thread(target=check_connection, daemon=True).start()

    def start_monitoring(self):
        from utils.config_management import get_param
        if get_param(self.dig_tool, "auto_rejoin_enabled"):
            self.status_monitor.start()

    def stop_monitoring(self):
        if hasattr(self.status_monitor, 'stop'):
            self.status_monitor.stop()

    def check_and_toggle_monitoring(self):
        from utils.config_management import get_param
        auto_rejoin_enabled = get_param(self.dig_tool, "auto_rejoin_enabled")
        if auto_rejoin_enabled and self.status_monitor._stop_event.is_set():
            self.status_monitor._stop_event.clear()
            self.status_monitor.start()
        elif not auto_rejoin_enabled and not self.status_monitor._stop_event.is_set():
            self.status_monitor.stop()
