import threading
from utils.debug_logger import logger


def select_item_area(dig_tool_instance):
    try:
        dig_tool_instance.update_status("Select item notification area...")
        
        def select_area_worker():
            try:
                dig_tool_instance.root.iconify()
                
                if not dig_tool_instance.item_ocr.initialized:
                    logger.info("Initializing OCR for item area selection")
                    if not dig_tool_instance.item_ocr.initialize_ocr():
                        dig_tool_instance.root.deiconify()
                        dig_tool_instance.update_status("Item OCR initialization failed")
                        return
                
                if dig_tool_instance.item_ocr.select_item_area():
                    if dig_tool_instance.item_ocr.item_area:
                        if 'item_area' not in dig_tool_instance.param_vars:
                            dig_tool_instance.param_vars['item_area'] = dig_tool_instance.settings_manager.get_param_type('item_area')()
                        dig_tool_instance.param_vars['item_area'].set(str(dig_tool_instance.item_ocr.item_area))
                        dig_tool_instance.settings_manager.save_all_settings()
                    
                    dig_tool_instance.update_status("Item area selected successfully")
                    logger.info("Item area selected for notifications")
                else:
                    dig_tool_instance.update_status("Item area selection cancelled")
                    logger.warning("Item area selection was cancelled")
                
                dig_tool_instance.root.deiconify()
                    
            except Exception as e:
                dig_tool_instance.root.deiconify()
                dig_tool_instance.update_status(f"Item area selection error: {e}")
                logger.error(f"Error in item area selection: {e}")
        
        threading.Thread(target=select_area_worker, daemon=True).start()
        
    except Exception as e:
        dig_tool_instance.update_status(f"Item area selection error: {e}")
        logger.error(f"Error in select_item_area: {e}")


def test_item_ocr(dig_tool_instance):
    try:
        if not dig_tool_instance.item_ocr.initialized:
            dig_tool_instance.update_status("Item OCR not initialized - select item area first")
            return
            
        if not dig_tool_instance.item_ocr.item_area:
            dig_tool_instance.update_status("Item area not set - select item area first")
            return
        
        dig_tool_instance.update_status("Testing item OCR...")
        
        def test_ocr_worker():
            try:
                item_text = dig_tool_instance.item_ocr.read_item_text()
                
                if item_text:
                    rarity = dig_tool_instance.item_ocr.extract_rarity(item_text)
                    if rarity:
                        dig_tool_instance.update_status(f"Item detected: {rarity} - {item_text[:50]}...")
                        logger.info(f"Test OCR successful - Rarity: {rarity}, Text: {item_text}")
                    else:
                        dig_tool_instance.update_status(f"Text detected but no rarity found: {item_text[:50]}...")
                        logger.info(f"Test OCR - No rarity found in: {item_text}")
                else:
                    dig_tool_instance.update_status("No item text detected - check area selection")
                    logger.warning("Test OCR failed - no item text detected")
                        
            except Exception as e:
                dig_tool_instance.update_status(f"Item OCR test error: {e}")
                logger.error(f"Error in item OCR test: {e}")
        
        threading.Thread(target=test_ocr_worker, daemon=True).start()
        
    except Exception as e:
        dig_tool_instance.update_status(f"Item OCR test error: {e}")
        logger.error(f"Error in test_item_ocr: {e}")
