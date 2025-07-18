import threading
from utils.debug_logger import logger


def select_money_area(dig_tool_instance):
    try:
        dig_tool_instance.update_status("Select money area for Discord notifications...")
        
        def select_area_worker():
            try:
                dig_tool_instance.root.iconify()
                
                if not dig_tool_instance.money_ocr.initialized:
                    logger.info("Initializing OCR for money area selection")
                    if not dig_tool_instance.money_ocr.initialize_ocr():
                        dig_tool_instance.root.deiconify()
                        dig_tool_instance.update_status("OCR initialization failed")
                        return
                
                if dig_tool_instance.money_ocr.select_money_area():
                    if dig_tool_instance.money_ocr.money_area:
                        if 'money_area' not in dig_tool_instance.param_vars:
                            dig_tool_instance.param_vars['money_area'] = dig_tool_instance.settings_manager.get_param_type('money_area')()
                        dig_tool_instance.param_vars['money_area'].set(str(dig_tool_instance.money_ocr.money_area))
                        dig_tool_instance.settings_manager.save_all_settings()
                    
                    dig_tool_instance.update_status("Money area selected successfully")
                    logger.info("Money area selected for Discord notifications")
                else:
                    dig_tool_instance.update_status("Money area selection cancelled")
                    logger.warning("Money area selection was cancelled")
                
                dig_tool_instance.root.deiconify()
                    
            except Exception as e:
                dig_tool_instance.root.deiconify()
                dig_tool_instance.update_status(f"Money area selection error: {e}")
                logger.error(f"Error in money area selection: {e}")
        
        threading.Thread(target=select_area_worker, daemon=True).start()
        
    except Exception as e:
        dig_tool_instance.update_status(f"Money area selection error: {e}")
        logger.error(f"Error in select_money_area: {e}")


def test_money_ocr(dig_tool_instance):
    try:
        if not dig_tool_instance.money_ocr.initialized:
            dig_tool_instance.update_status("OCR not initialized - select money area first")
            return
            
        if not dig_tool_instance.money_ocr.money_area:
            dig_tool_instance.update_status("Money area not set - select money area first")
            return
        
        dig_tool_instance.update_status("Testing money OCR...")
        
        def test_ocr_worker():
            try:
                money_value = dig_tool_instance.money_ocr.read_money_value()
                
                if money_value:
                    dig_tool_instance.update_status(f"Money detected: {money_value}")
                    logger.info(f"Test OCR successful - Money: {money_value}")
                else:
                    dig_tool_instance.update_status("No money detected - check area selection")
                    logger.warning("Test OCR failed - no money value detected")
                        
            except Exception as e:
                dig_tool_instance.update_status(f"Money OCR test error: {e}")
                logger.error(f"Error in money OCR test: {e}")
        
        threading.Thread(target=test_ocr_worker, daemon=True).start()
        
    except Exception as e:
        dig_tool_instance.update_status(f"Money OCR test error: {e}")
        logger.error(f"Error in test_money_ocr: {e}")
