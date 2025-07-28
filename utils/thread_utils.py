import threading
import time
from utils.debug_logger import logger


def start_threads(instance):
    if instance.hotkey_thread is None or not instance.hotkey_thread.is_alive():
        instance.hotkey_thread = threading.Thread(
            target=run_hotkey_listener, args=(instance,), daemon=True
        )
        instance.hotkey_thread.start()
    if instance.main_loop_thread is None or not instance.main_loop_thread.is_alive():
        instance.main_loop_thread = threading.Thread(
            target=instance.run_main_loop, daemon=True
        )
        instance.main_loop_thread.start()
    
    if hasattr(instance, 'roblox_rejoiner'):
        instance.roblox_rejoiner.start_monitoring()


def run_hotkey_listener(instance):
    logger.info("Hotkey listener thread started")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            from utils.input_management import apply_keybinds
            instance.root.after(0, lambda: apply_keybinds(instance))
            logger.debug(f"Keybind application scheduled (attempt {attempt + 1})")
            break
        except Exception as e:
            logger.error(
                f"Failed to schedule keybind application (attempt {attempt + 1}): {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(1)
    
    while instance.preview_active:
        time.sleep(0.5)


def check_shutdown(instance):
    hotkey_alive = instance.hotkey_thread and instance.hotkey_thread.is_alive()
    main_loop_alive = instance.main_loop_thread and instance.main_loop_thread.is_alive()
    if hotkey_alive or main_loop_alive:
        instance.root.after(100, lambda: check_shutdown(instance))
    else:
        from utils.system_utils import perform_final_cleanup
        perform_final_cleanup(instance)


def run_in_background(target, *args):
    threading.Thread(target=target, args=args, daemon=True).start()


def create_daemon_thread(target, args=None, name=None):
    thread = threading.Thread(
        target=target,
        args=args or (),
        daemon=True,
        name=name
    )
    return thread


def safe_thread_start(thread, max_retries=3):
    for attempt in range(max_retries):
        try:
            thread.start()
            logger.debug(f"Thread {thread.name or 'unnamed'} started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start thread (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1)
    return False


def wait_for_thread_completion(thread, timeout=5.0):
    if thread and thread.is_alive():
        thread.join(timeout=timeout)
        if thread.is_alive():
            logger.warning(f"Thread {thread.name or 'unnamed'} did not complete within {timeout}s")
            return False
        else:
            logger.debug(f"Thread {thread.name or 'unnamed'} completed successfully")
            return True
    return True


def cleanup_thread_pool(thread_pool, max_threads=10):
    if not thread_pool:
        return thread_pool
    
    active_threads = [t for t in thread_pool if t.is_alive()]
    
    if len(active_threads) >= max_threads:
        logger.warning(f"Thread pool has {len(active_threads)} active threads, waiting for cleanup")
        time.sleep(0.1)
        active_threads = [t for t in thread_pool if t.is_alive()]
    
    return active_threads
