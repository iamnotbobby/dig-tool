import tkinter as tk
import asyncio
from PIL import Image, ImageEnhance
import io
import pyautogui
import numpy as np
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

from utils.debug_logger import logger


class MoneyOCR:
    def __init__(self):
        self.ocr_engine = None
        self.money_area = None
        self.initialized = False
        
    def initialize_ocr(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.ocr_engine = OcrEngine.try_create_from_user_profile_languages()
            self.initialized = bool(self.ocr_engine)
            return self.initialized
        except Exception as e:
            logger.error(f"OCR initialization failed: {e}")
            return False
    
    def select_money_area(self):
        try:
            selector = AreaSelector()
            self.money_area = selector.select_area()
            return bool(self.money_area)
        except Exception as e:
            logger.error(f"Area selection failed: {e}")
            return False
    
    def read_money_value(self, max_retries=2, retry_delay=0.3):
        if not self.initialized or not self.money_area:
            return None
        
        debug_ocr_results = []
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import time
                    time.sleep(retry_delay)
                    logger.debug(f"Money OCR retry attempt {attempt + 1}/{max_retries}")
                
                x, y, width, height = self.money_area
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                
                enhanced_images = self._enhance_for_green_text(screenshot)
                
                attempt_results = []
                
                priority_methods = ["original", "scaled_2x", "green_channel_3x"]
                
                for priority_name in priority_methods:
                    for name, img in enhanced_images:
                        if name == priority_name:
                            try:
                                try:
                                    loop = asyncio.get_event_loop()
                                    if loop.is_closed():
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                except RuntimeError:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                
                                result = loop.run_until_complete(self._ocr_single_image(img, name))
                                attempt_results.append((name, result or ""))
                                
                                if result and result.strip():
                                    clean_text = self._clean_money_text(result)
                                    if clean_text:
                                        formatted_money = self._format_money_value(clean_text)
                                        logger.info(f"Money detected: {formatted_money} (method: {name}, attempt: {attempt + 1})")
                                        return formatted_money
                                    else:
                                        logger.debug(f"OCR text '{result}' from {name} didn't match money patterns")
                                else:
                                    logger.debug(f"No text detected from {name}")
                            except Exception as e:
                                logger.debug(f"OCR failed for {name}: {e}")
                                attempt_results.append((name, f"ERROR: {e}"))
                            break
                
                if attempt == 0:
                    tried_methods = {result[0] for result in attempt_results}
                    for name, img in enhanced_images:
                        if name in tried_methods or len(attempt_results) >= 6:
                            continue
                        
                        try:
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_closed():
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            
                            result = loop.run_until_complete(self._ocr_single_image(img, name))
                            attempt_results.append((name, result or ""))
                            
                            if result and result.strip():
                                clean_text = self._clean_money_text(result)
                                if clean_text:
                                    formatted_money = self._format_money_value(clean_text)
                                    logger.info(f"Money detected: {formatted_money} (method: {name}, attempt: {attempt + 1})")
                                    return formatted_money
                                else:
                                    logger.debug(f"OCR text '{result}' from {name} didn't match money patterns")
                            else:
                                logger.debug(f"No text detected from {name}")
                        except Exception as e:
                            logger.debug(f"OCR failed for {name}: {e}")
                            attempt_results.append((name, f"ERROR: {e}"))
                            continue
                
                debug_ocr_results.append((attempt + 1, attempt_results))
                
                if attempt < max_retries - 1:
                    logger.debug(f"No money detected on attempt {attempt + 1}, retrying...")
                    
            except Exception as e:
                logger.error(f"Money OCR attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
        
        logger.warning("No money value detected after all retry attempts")
        return None
    
    def test_money_ocr(self):
        if not self.initialized or not self.money_area:
            return None
        
        try:
            x, y, width, height = self.money_area
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            
            enhanced_images = self._enhance_for_green_text(screenshot)
            
            for name, img in enhanced_images:
                try:
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    result = loop.run_until_complete(self._ocr_single_image(img, name))
                    
                    if result and result.strip():
                        clean_text = self._clean_money_text(result)
                        if clean_text:
                            formatted_money = self._format_money_value(clean_text)
                            logger.info(f"Test OCR successful - Money: {formatted_money} (method: {name})")
                            return formatted_money
                        else:
                            logger.debug(f"OCR text '{result}' from {name} didn't match money patterns")
                    else:
                        logger.debug(f"No text detected from {name}")
                except Exception as e:
                    logger.debug(f"OCR failed for {name}: {e}")
                    continue
            
            logger.warning("Test OCR failed - no money value detected with any method")
            return None
            
        except Exception as e:
            logger.error(f"Test OCR error: {e}")
            return None

    def read_money_from_screenshot(self, full_screenshot, max_retries=3, retry_delay=0.5):
        if not self.initialized or not self.money_area:
            return None
        
        x, y, width, height = self.money_area
        cropped_screenshot = full_screenshot.crop((x, y, x + width, y + height))
        
        debug_ocr_results = []
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import time
                    time.sleep(retry_delay)
                    logger.debug(f"Money OCR retry attempt {attempt + 1}/{max_retries}")
                
                enhanced_images = self._enhance_for_green_text(cropped_screenshot)
                
                attempt_results = []
                
                for name, img in enhanced_images:
                    try:
                        if name == "green_channel_6x":
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_closed():
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            
                            result = loop.run_until_complete(self._ocr_single_image(img, name))
                            attempt_results.append((name, result or ""))
                            
                            if result and result.strip():
                                clean_text = self._clean_money_text(result)
                                if clean_text:
                                    formatted_money = self._format_money_value(clean_text)
                                    logger.info(f"Money detected: {formatted_money} (method: {name}, attempt: {attempt + 1})")
                                    return formatted_money
                                else:
                                    logger.debug(f"OCR text '{result}' from {name} didn't match money patterns")
                            else:
                                logger.debug(f"No text detected from {name}")
                    except Exception as e:
                        logger.debug(f"OCR failed for {name}: {e}")
                        attempt_results.append((name, f"ERROR: {e}"))
                        continue
                
                for name, img in enhanced_images:
                    if name == "green_channel_6x":
                        continue
                    
                    try:
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_closed():
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        result = loop.run_until_complete(self._ocr_single_image(img, name))
                        attempt_results.append((name, result or ""))
                        
                        if result and result.strip():
                            clean_text = self._clean_money_text(result)
                            if clean_text:
                                formatted_money = self._format_money_value(clean_text)
                                logger.info(f"Money detected: {formatted_money} (method: {name}, attempt: {attempt + 1})")
                                return formatted_money
                            else:
                                logger.debug(f"OCR text '{result}' from {name} didn't match money patterns")
                        else:
                            logger.debug(f"No text detected from {name}")
                    except Exception as e:
                        logger.debug(f"OCR failed for {name}: {e}")
                        attempt_results.append((name, f"ERROR: {e}"))
                        continue
                
                debug_ocr_results.append((attempt + 1, attempt_results))
                
                if attempt < max_retries - 1:
                    logger.debug(f"No money detected on attempt {attempt + 1}, retrying...")
                    
            except Exception as e:
                logger.error(f"Money OCR attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
        
        logger.warning("No money value detected after all retry attempts")
        return None
    
    def get_debug_info(self):
        return []
    
    def _enhance_for_green_text(self, image):
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        if image.size[0] < 10 or image.size[1] < 10:
            return [("original", image)]
        
        enhanced_images = []
        img_array = np.array(image)
        
        enhanced_images.append(("original", image))
        
        try:
            scaled_2x = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
            enhanced_images.append(("scaled_2x", scaled_2x))
            
            scaled_3x = image.resize((image.width * 3, image.height * 3), Image.Resampling.LANCZOS)
            enhanced_images.append(("scaled_3x", scaled_3x))
        except Exception:
            pass
        
        try:
            r, g, b = image.split()
            g_enhanced = ImageEnhance.Contrast(g).enhance(3.0)
            green_only = g_enhanced.convert('RGB')
            
            scaled_3x = green_only.resize(
                (green_only.width * 3, green_only.height * 3), 
                Image.Resampling.LANCZOS
            )
            enhanced_images.append(("green_channel_3x", scaled_3x))
        except Exception:
            pass
        
        try:
            green_ranges = [
                {'low': np.array([154, 245, 129]), 'high': np.array([174, 255, 149])},
                {'low': np.array([149, 240, 124]), 'high': np.array([179, 255, 154])},
            ]
            
            green_mask = np.zeros(img_array.shape[:2], dtype=bool)
            for range_def in green_ranges:
                mask = np.all((img_array >= range_def['low']) & (img_array <= range_def['high']), axis=2)
                green_mask = green_mask | mask
            
            if np.any(green_mask):
                result = np.zeros_like(img_array)
                result[green_mask] = [255, 255, 255]
                result[~green_mask] = [0, 0, 0]
                green_isolated = Image.fromarray(result)
                
                scaled_3x = green_isolated.resize(
                    (green_isolated.width * 3, green_isolated.height * 3), 
                    Image.Resampling.LANCZOS
                )
                enhanced_images.append(("target_green_3x", scaled_3x))
        except Exception:
            pass
        
        try:
            from PIL import ImageFilter
            
            scaled_4x = image.resize((image.width * 4, image.height * 4), Image.Resampling.LANCZOS)
            enhanced_images.append(("scaled_4x", scaled_4x))
            
            sharp_3x = scaled_3x.filter(ImageFilter.SHARPEN)
            enhanced_images.append(("scaled_3x_sharp", sharp_3x))
            
            contrast_enhanced = ImageEnhance.Contrast(scaled_3x).enhance(2.5)
            enhanced_images.append(("scaled_3x_contrast", contrast_enhanced))
            
            grayscale = scaled_3x.convert('L')
            binary_180 = grayscale.point(lambda x: 255 if x > 180 else 0, '1').convert('RGB')
            enhanced_images.append(("scaled_3x_binary", binary_180))
            
        except Exception:
            pass
        
        return enhanced_images
    
    async def _ocr_single_image(self, image, image_name="unknown"):
        try:
            if not self.ocr_engine:
                return ""
                
            img_byte_arr = io.BytesIO()
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(img_byte_arr, format='PNG', optimize=False)
            img_bytes = img_byte_arr.getvalue()
            
            stream = InMemoryRandomAccessStream()
            data_writer = DataWriter(stream.get_output_stream_at(0))
            data_writer.write_bytes(img_bytes)
            
            await data_writer.store_async()
            decoder = await BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()
            ocr_result = await self.ocr_engine.recognize_async(software_bitmap)
            
            return ocr_result.text if ocr_result.text else ""
            
        except Exception as e:
            return ""
    
    def _clean_money_text(self, text):
        if not text:
            return None
            
        import re
        
        text = text.strip()
        text = text.replace('O', '0').replace('l', '1').replace('I', '1')
        text = re.sub(r'\$+', '$', text)
        
        abbreviation_pattern = r'(\d+\.?\d*)\s*([kmgtKMGT])\b'
        abbreviation_match = re.search(abbreviation_pattern, text)
        
        if abbreviation_match:
            number_part = abbreviation_match.group(1)
            suffix = abbreviation_match.group(2).upper()
            
            try:
                float(number_part)
                return f"{number_part}{suffix}"
            except ValueError:
                pass
        
        digits_only = re.sub(r'[^\d]', '', text)
        
        if not digits_only or len(digits_only) == 0:
            return None
            
        return digits_only
    
    def _format_money_value(self, money_text):
        if not money_text:
            return money_text
            
        import re
        
        if re.match(r'^\d+\.?\d*[KMGTkmgt]$', money_text):
            return f"${money_text}"
        
        if money_text.isdigit():
            try:
                num = int(money_text)
                return f"${num:,}"
            except ValueError:
                return f"${money_text}"
        
        clean_text = money_text.replace('$', '')
        clean_number = re.sub(r'[^\d.]', '', clean_text)
        
        if not clean_number:
            return money_text
        
        try:
            num = float(clean_number)
            if num >= 1000:
                return f"${num:,.0f}"
            else:
                return f"${num:.2f}"
        except ValueError:
            return money_text


class AreaSelector:
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.selecting = False
        
    def select_area(self):
        root = tk.Tk()
        root.attributes('-fullscreen', True)
        root.attributes('-alpha', 0.3)
        root.attributes('-topmost', True)
        root.configure(bg='#1a1a1a', cursor='crosshair')
        
        selection_rect = tk.Frame(
            root,
            highlightthickness=2,
            highlightbackground="#00ff88",
            highlightcolor="#00ff88",
            bd=0,
            relief="solid"
        )
        selection_rect.configure(highlightthickness=2)
        
        def on_mouse_down(event):
            self.start_x = event.x_root
            self.start_y = event.y_root
            self.selecting = True
            selection_rect.place(x=event.x, y=event.y, width=1, height=1)
            
        def on_mouse_drag(event):
            if self.selecting:
                self.end_x = event.x_root
                self.end_y = event.y_root
                
                if (self.start_x is not None and self.end_x is not None and 
                    self.start_y is not None and self.end_y is not None):
                    x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
                    x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
                    
                    overlay_x = root.winfo_rootx()
                    overlay_y = root.winfo_rooty()
                    
                    selection_rect.place(
                        x=x1 - overlay_x,
                        y=y1 - overlay_y,
                        width=x2 - x1,
                        height=y2 - y1
                    )
                
        def on_mouse_up(event):
            self.selecting = False
            self.end_x = event.x_root
            self.end_y = event.y_root
            root.quit()
            
        def on_escape(event):
            self.start_x = self.start_y = self.end_x = self.end_y = None
            root.quit()
            
        root.bind("<Button-1>", on_mouse_down)
        root.bind("<B1-Motion>", on_mouse_drag)
        root.bind("<ButtonRelease-1>", on_mouse_up)
        root.bind("<Escape>", on_escape)
        root.bind("<KeyPress-Escape>", on_escape)
        
        root.focus_set()
        
        root.mainloop()
        root.destroy()
        
        if all(coord is not None for coord in [self.start_x, self.start_y, self.end_x, self.end_y]):
            x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)  # type: ignore
            x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)  # type: ignore
            result = (x1, y1, x2 - x1, y2 - y1)
            logger.info(f"Money area selected: {x2-x1}x{y2-y1} at ({x1},{y1})")
            return result
        return None


class ItemAreaSelector:
    def __init__(self):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.selecting = False
        
    def select_area(self):
        root = tk.Tk()
        root.attributes('-fullscreen', True)
        root.attributes('-alpha', 0.3)
        root.attributes('-topmost', True)
        root.configure(bg='#1a1a1a', cursor='crosshair')
        
        selection_rect = tk.Frame(
            root,
            highlightthickness=2,
            highlightbackground="#4da6ff",
            highlightcolor="#4da6ff",
            bd=0,
            relief="solid"
        )
        selection_rect.configure(highlightthickness=2)
        
        def on_mouse_down(event):
            self.start_x = event.x_root
            self.start_y = event.y_root
            self.selecting = True
            selection_rect.place(x=event.x, y=event.y, width=1, height=1)
            
        def on_mouse_drag(event):
            if self.selecting:
                self.end_x = event.x_root
                self.end_y = event.y_root
                
                if (self.start_x is not None and self.end_x is not None and 
                    self.start_y is not None and self.end_y is not None):
                    x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
                    x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
                    
                    overlay_x = root.winfo_rootx()
                    overlay_y = root.winfo_rooty()
                    
                    selection_rect.place(
                        x=x1 - overlay_x,
                        y=y1 - overlay_y,
                        width=x2 - x1,
                        height=y2 - y1
                    )
                
        def on_mouse_up(event):
            self.selecting = False
            self.end_x = event.x_root
            self.end_y = event.y_root
            root.quit()
            
        def on_escape(event):
            self.start_x = self.start_y = self.end_x = self.end_y = None
            root.quit()
            
        root.bind("<Button-1>", on_mouse_down)
        root.bind("<B1-Motion>", on_mouse_drag)
        root.bind("<ButtonRelease-1>", on_mouse_up)
        root.bind("<Escape>", on_escape)
        root.bind("<KeyPress-Escape>", on_escape)
        
        root.focus_set()
        
        root.mainloop()
        root.destroy()
        
        if all(coord is not None for coord in [self.start_x, self.start_y, self.end_x, self.end_y]):
            x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
            x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
            result = (x1, y1, x2 - x1, y2 - y1)
            logger.info(f"Item area selected: {x2-x1}x{y2-y1} at ({x1},{y1})")
            return result
        return None


class ItemOCR:
    def __init__(self):
        self.ocr_engine = None
        self.item_area = None
        self.initialized = False
        logger.debug("ItemOCR: Initialized with empty state")
        
    def initialize_ocr(self):
        logger.debug("ItemOCR: Attempting to initialize OCR engine")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.ocr_engine = OcrEngine.try_create_from_user_profile_languages()
            self.initialized = bool(self.ocr_engine)
            logger.debug(f"ItemOCR: OCR engine initialization {'successful' if self.initialized else 'failed'}")
            return self.initialized
        except Exception as e:
            logger.error(f"Item OCR initialization failed: {e}")
            return False
    
    def select_item_area(self):
        logger.debug("ItemOCR: Starting item area selection")
        try:
            selector = ItemAreaSelector()
            self.item_area = selector.select_area()
            if self.item_area:
                logger.debug(f"ItemOCR: Item area selected: {self.item_area}")
            else:
                logger.debug("ItemOCR: No item area selected")
            return bool(self.item_area)
        except Exception as e:
            logger.error(f"Item area selection failed: {e}")
            return False
    
    def read_item_text(self, max_retries=2, retry_delay=0.3):
        logger.debug(f"read_item_text: Starting with max_retries={max_retries}, retry_delay={retry_delay}")
        
        if not self.initialized or not self.item_area:
            logger.debug(f"read_item_text: Not ready - initialized: {self.initialized}, item_area: {self.item_area}")
            return None
            
        for attempt in range(max_retries):
            logger.debug(f"read_item_text: Attempt {attempt + 1}/{max_retries}")
            
            try:
                if attempt > 0:
                    import time
                    logger.debug(f"read_item_text: Waiting {retry_delay}s before retry")
                    time.sleep(retry_delay)
                
                x, y, width, height = self.item_area
                logger.debug(f"read_item_text: Taking screenshot of area ({x}, {y}, {width}, {height})")
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                
                logger.debug(f"read_item_text: Screenshot taken, size: {screenshot.size}")
                enhanced_images = self._enhance_for_rarity_colors(screenshot)
                logger.debug(f"read_item_text: Generated {len(enhanced_images)} enhanced images")
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        logger.debug("read_item_text: Event loop is running, creating new one")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    logger.debug("read_item_text: RuntimeError, creating new event loop")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                for idx, (name, img) in enumerate(enhanced_images):
                    logger.debug(f"read_item_text: Processing enhancement method {idx + 1}/{len(enhanced_images)}: '{name}'")
                    
                    try:
                        result = loop.run_until_complete(self._ocr_single_image(img, name))
                        logger.debug(f"read_item_text: OCR result from '{name}': '{result}'")
                        
                        if result and result.strip():
                            rarity = self.extract_rarity(result)
                            logger.debug(f"read_item_text: Extracted rarity: {rarity}")
                            
                            if rarity:
                                logger.info(f"Item detected: {rarity} (method: {name}, attempt: {attempt + 1})")
                                cleaned_result = self.clean_item_text(result)
                                logger.debug(f"Original OCR text: '{result}', Cleaned: '{cleaned_result}'")
                                try:
                                    loop.close()
                                except:
                                    pass
                                logger.debug(f"read_item_text: Returning successful result: '{cleaned_result}'")
                                return cleaned_result
                            else:
                                logger.debug(f"read_item_text: No rarity found in result '{result}' from method '{name}'")
                        else:
                            logger.debug(f"read_item_text: Empty or whitespace result from method '{name}'")
                    except Exception as e:
                        logger.debug(f"read_item_text: Exception with method '{name}': {e}")
                        continue
                
                try:
                    loop.close()
                except:
                    pass
                    
                logger.debug(f"read_item_text: Attempt {attempt + 1} completed with no valid results")
                    
            except Exception as e:
                logger.error(f"Item OCR attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
        
        logger.debug("read_item_text: All attempts exhausted, returning None")
        return None
    
    def extract_rarity(self, text):
        logger.debug(f"extract_rarity: Input text: '{text}'")
        
        if not text:
            logger.debug("extract_rarity: Empty text, returning None")
            return None
        
        rarities = ['Junk', 'Common', 'Unusual', 'Scarce', 'Legendary', 'Mythical', 'Divine', 'Prismatic']
        
        text_upper = text.upper()
        logger.debug(f"extract_rarity: Text uppercase: '{text_upper}'")
        
        found_rarities = []
        for rarity in rarities:
            rarity_upper = rarity.upper()
            start_pos = 0
            while True:
                pos = text_upper.find(rarity_upper, start_pos)
                if pos == -1:
                    break
                found_rarities.append((pos, rarity))
                start_pos = pos + len(rarity_upper)
        
        if not found_rarities:
            logger.debug("extract_rarity: No rarity found in text")
            return None
        
        found_rarities.sort(key=lambda x: x[0])
        logger.debug(f"extract_rarity: Found rarities at positions: {found_rarities}")
        
        if len(found_rarities) == 1:
            rarity = found_rarities[0][1]
            logger.debug(f"extract_rarity: Single rarity found: '{rarity}'")
            return rarity
        elif len(found_rarities) >= 2:
            first_rarity = found_rarities[0][1]
            second_rarity = found_rarities[1][1]
            
            logger.debug(f"extract_rarity: Multiple rarities detected - First: '{first_rarity}', Second: '{second_rarity}'")
            
            if first_rarity.upper() == second_rarity.upper():
                logger.debug(f"extract_rarity: Duplicate rarity detected, returning second occurrence: '{second_rarity}'")
                return second_rarity
            else:
                logger.debug(f"extract_rarity: Different rarities detected, returning second (more recent): '{second_rarity}'")
                return second_rarity
        
        logger.debug(f"extract_rarity: Fallback - returning first rarity: '{found_rarities[0][1]}'")
        return found_rarities[0][1]
    
    def clean_item_text(self, text):
        """Clean and format item text, extracting rarity and text after it"""
        logger.debug(f"clean_item_text: Input text: '{text}'")
        
        if not text:
            logger.debug("clean_item_text: Empty text input, returning as-is")
            return text
        
        cleaned = ' '.join(text.split())
        logger.debug(f"clean_item_text: After whitespace join: '{cleaned}'")
        
        artifacts_to_remove = ['|', '_', '~', '`', '\x00', '\ufffd']
        original_cleaned = cleaned
        for artifact in artifacts_to_remove:
            cleaned = cleaned.replace(artifact, '')
        if original_cleaned != cleaned:
            logger.debug(f"clean_item_text: After artifact removal: '{cleaned}'")
        
        import re
        before_spaces = cleaned
        cleaned = re.sub(r'\s+', ' ', cleaned)
        if before_spaces != cleaned:
            logger.debug(f"clean_item_text: After space cleanup: '{cleaned}'")
        
        rarities = ['Junk', 'Common', 'Unusual', 'Scarce', 'Legendary', 'Mythical', 'Divine', 'Prismatic']
        logger.debug(f"clean_item_text: Searching for rarities in: '{cleaned}'")
        
        cleaned_upper = cleaned.upper()
        
        found_rarities = []
        for rarity in rarities:
            rarity_upper = rarity.upper()
            start_pos = 0
            while True:
                pos = cleaned_upper.find(rarity_upper, start_pos)
                if pos == -1:
                    break
                found_rarities.append((pos, rarity))
                start_pos = pos + len(rarity_upper)
        
        if found_rarities:
            found_rarities.sort(key=lambda x: x[0])
            logger.debug(f"clean_item_text: Found rarities at positions: {found_rarities}")
            
            target_rarity = None
            target_position = None
            
            if len(found_rarities) == 1:
                target_position, target_rarity = found_rarities[0]
                logger.debug(f"clean_item_text: Using single rarity '{target_rarity}' at position {target_position}")
            elif len(found_rarities) >= 2:
                target_position, target_rarity = found_rarities[1]
                logger.debug(f"clean_item_text: Using second rarity '{target_rarity}' at position {target_position} (stacking logic)")
            
            if target_rarity and target_position is not None:
                logger.debug(f"clean_item_text: Found target rarity '{target_rarity}' at position {target_position}")
                result = target_rarity.title()
                logger.debug(f"clean_item_text: Returning rarity only: '{result}'")
                return result
        
        result = cleaned.title().strip()
        logger.debug(f"clean_item_text: No rarity found, returning cleaned text: '{result}'")
        return result
    
    def _enhance_for_rarity_colors(self, image):
        logger.debug(f"_enhance_for_rarity_colors: Input image size: {image.size}, mode: {image.mode}")
        
        if image.mode != 'RGB':
            logger.debug(f"_enhance_for_rarity_colors: Converting from {image.mode} to RGB")
            image = image.convert('RGB')
        
        if image.size[0] < 10 or image.size[1] < 10:
            logger.debug("_enhance_for_rarity_colors: Image too small, returning original only")
            return [("original", image)]
        
        enhanced_images = []
        img_array = np.array(image)
        logger.debug(f"_enhance_for_rarity_colors: Image array shape: {img_array.shape}")
        
        try:
            color_preserved_image = self._create_color_preserved_image(img_array)
            if color_preserved_image is not None:
                enhanced_images.append(("color_preserved", color_preserved_image))
                logger.debug("_enhance_for_rarity_colors: Added color_preserved image")
                
                black_text_image = self._convert_colors_to_black(color_preserved_image)
                if black_text_image is not None:
                    enhanced_images.append(("color_preserved_black_text", black_text_image))
                    logger.debug("_enhance_for_rarity_colors: Added color_preserved_black_text image")
                
                for scale in [2, 3]:
                    try:
                        scaled_color = color_preserved_image.resize(
                            (color_preserved_image.width * scale, color_preserved_image.height * scale), 
                            Image.Resampling.LANCZOS
                        )
                        enhanced_images.append((f"color_preserved_scaled_{scale}x", scaled_color))
                        
                        if black_text_image is not None:
                            scaled_black = black_text_image.resize(
                                (black_text_image.width * scale, black_text_image.height * scale), 
                                Image.Resampling.LANCZOS
                            )
                            enhanced_images.append((f"color_preserved_black_text_scaled_{scale}x", scaled_black))
                    except Exception as e:
                        logger.debug(f"_enhance_for_rarity_colors: Failed to scale color preserved images: {e}")
        except Exception as e:
            logger.debug(f"_enhance_for_rarity_colors: Exception in color preservation: {e}")
        
        try:
            contrast_enhanced = ImageEnhance.Contrast(image).enhance(2.5)
            enhanced_images.append(("contrast_enhanced", contrast_enhanced))
            
            brightness_enhanced = ImageEnhance.Brightness(contrast_enhanced).enhance(1.2)
            enhanced_images.append(("brightness_contrast", brightness_enhanced))
        except Exception:
            pass
        
        try:
            for scale in [2, 3]:
                scaled = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
                enhanced_images.append((f"scaled_{scale}x", scaled))
        except Exception:
            pass
        
        enhanced_images.append(("original", image))
        logger.debug(f"_enhance_for_rarity_colors: Generated {len(enhanced_images)} total enhanced images")
        for idx, (name, _) in enumerate(enhanced_images):
            logger.debug(f"_enhance_for_rarity_colors: Image {idx + 1}: '{name}'")
        return enhanced_images
    
    def _create_color_preserved_image(self, img_array):
        logger.debug("_create_color_preserved_image: Starting multi-tolerance color preservation")
        
        try:
            rarity_colors = {
                'divine': {'hex': '#f32626', 'rgb': (243, 38, 38), 'tolerances': [35, 50, 70]},
                'legendary': {'hex': '#fca43c', 'rgb': (252, 164, 60), 'tolerances': [35, 50, 70]},
                'mythical': {'hex': '#e561a6', 'rgb': (229, 97, 166), 'tolerances': [40, 60, 80]},
                'scarce': {'hex': "#846bd9", 'rgb': (132, 107, 217), 'tolerances': [35, 50, 70]},
                'prismatic_P': {'hex': '#f5808b', 'rgb': (245, 128, 139), 'tolerances': [30, 45, 65]},
                'prismatic_R': {'hex': '#f79a87', 'rgb': (247, 154, 135), 'tolerances': [30, 45, 65]},
                'prismatic_I1': {'hex': '#fcbb8e', 'rgb': (252, 187, 142), 'tolerances': [30, 45, 65]},
                'prismatic_S': {'hex': '#fad090', 'rgb': (250, 208, 144), 'tolerances': [30, 45, 65]},
                'prismatic_M': {'hex': '#ebe98e', 'rgb': (235, 233, 142), 'tolerances': [30, 45, 65]},
                'prismatic_A': {'hex': '#e6fd80', 'rgb': (230, 253, 128), 'tolerances': [30, 45, 65]},
                'prismatic_T': {'hex': '#e1fa7d', 'rgb': (225, 250, 125), 'tolerances': [30, 45, 65]},
                'prismatic_I2': {'hex': '#d0f9a2', 'rgb': (208, 249, 162), 'tolerances': [30, 45, 65]},
                'prismatic_C': {'hex': '#c7ffac', 'rgb': (199, 255, 172), 'tolerances': [30, 45, 65]},
            }
            
            img_hsv = self._convert_to_hsv_safe(img_array)
            
            rarity_mask = np.zeros(img_array.shape[:2], dtype=bool)
            total_rarity_pixels = 0
            detection_results = {}
            
            for color_name, color_info in rarity_colors.items():
                target_rgb = np.array(color_info['rgb'])
                best_tolerance = None
                best_pixels = 0
                
                for tolerance in color_info['tolerances']:
                    color_diff = np.sqrt(np.sum((img_array - target_rgb) ** 2, axis=2))
                    rgb_mask = color_diff <= tolerance
                    rgb_pixels = np.sum(rgb_mask)
                    
                    hsv_pixels = 0
                    if img_hsv is not None:
                        hsv_mask = self._create_hsv_color_mask(img_hsv, target_rgb, tolerance)
                        if hsv_mask is not None:
                            hsv_pixels = np.sum(hsv_mask)
                    
                    current_pixels = max(rgb_pixels, hsv_pixels)
                    
                    if current_pixels > best_pixels:
                        best_pixels = current_pixels
                        best_tolerance = tolerance
                        
                        if hsv_pixels > rgb_pixels and img_hsv is not None:
                            color_mask = hsv_mask
                            detection_method = "HSV"
                        else:
                            color_mask = rgb_mask
                            detection_method = "RGB"
                    
                    if current_pixels > 50:
                        break
                
                if best_pixels > 0:
                    logger.debug(f"_create_color_preserved_image: Found {best_pixels} pixels for {color_name} ({color_info['hex']}) using {detection_method} method with tolerance {best_tolerance}")
                    rarity_mask = rarity_mask | color_mask
                    total_rarity_pixels += best_pixels
                    detection_results[color_name] = {'pixels': best_pixels, 'tolerance': best_tolerance, 'method': detection_method}
            
            logger.debug(f"_create_color_preserved_image: Total rarity pixels found: {total_rarity_pixels}")
            logger.debug(f"_create_color_preserved_image: Detection summary: {detection_results}")
            
            if total_rarity_pixels > 0:
                result = np.full_like(img_array, 255)
                result[rarity_mask] = img_array[rarity_mask]
                
                preserved_image = Image.fromarray(result)
                logger.debug(f"_create_color_preserved_image: Successfully created color preserved image")
                return preserved_image
            else:
                logger.debug("_create_color_preserved_image: No rarity colors found with any tolerance level")
                return None
                
        except Exception as e:
            logger.debug(f"_create_color_preserved_image: Exception: {e}")
            return None
    
    def _convert_colors_to_black(self, color_preserved_image):
        logger.debug("_convert_colors_to_black: Converting preserved colors to black")
        
        try:
            img_array = np.array(color_preserved_image)
            
            white_threshold = 250
            non_white_mask = np.any(img_array < white_threshold, axis=2)
            
            black_pixels_count = np.sum(non_white_mask)
            logger.debug(f"_convert_colors_to_black: Converting {black_pixels_count} colored pixels to black")
            
            if black_pixels_count > 0:
                result = np.full_like(img_array, 255)
                result[non_white_mask] = [0, 0, 0]
                
                black_text_image = Image.fromarray(result)
                logger.debug("_convert_colors_to_black: Successfully created black text image")
                return black_text_image
            else:
                logger.debug("_convert_colors_to_black: No colored pixels to convert")
                return None
                
        except Exception as e:
            logger.debug(f"_convert_colors_to_black: Exception: {e}")
            return None
    
    def _convert_to_hsv_safe(self, img_array):
        """Safely convert RGB to HSV, handling potential issues"""
        try:
            import cv2
            img_bgr = img_array[:, :, ::-1]  
            img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            logger.debug("_convert_to_hsv_safe: Successfully converted to HSV using OpenCV")
            return img_hsv
        except ImportError:
            logger.debug("_convert_to_hsv_safe: OpenCV not available")
        except Exception as e:
            logger.debug(f"_convert_to_hsv_safe: OpenCV conversion failed: {e}")
        
        try:
            def rgb_to_hsv_manual(r, g, b):
                r, g, b = r/255.0, g/255.0, b/255.0
                max_val = max(r, g, b)
                min_val = min(r, g, b)
                diff = max_val - min_val
                
                v = max_val
                
                s = 0 if max_val == 0 else diff / max_val
                
                if diff == 0:
                    h = 0
                elif max_val == r:
                    h = (60 * ((g - b) / diff) + 360) % 360
                elif max_val == g:
                    h = (60 * ((b - r) / diff) + 120) % 360
                else:
                    h = (60 * ((r - g) / diff) + 240) % 360
                
                return h, s * 255, v * 255 
            
            height, width = img_array.shape[:2]
            hsv_array = np.zeros((height, width, 3), dtype=np.uint8)
            
            for i in range(height):
                for j in range(width):
                    r, g, b = img_array[i, j]
                    h, s, v = rgb_to_hsv_manual(r, g, b)
                    hsv_array[i, j] = [h/2, s, v]  
            
            logger.debug("_convert_to_hsv_safe: Successfully converted using manual method")
            return hsv_array
        except Exception as e:
            logger.debug(f"_convert_to_hsv_safe: Manual conversion failed: {e}")
            return None
    
    def _create_hsv_color_mask(self, img_hsv, target_rgb, tolerance):
        """Create a color mask using HSV color space for better cross-screen compatibility"""
        try:
            target_hsv = self._rgb_to_hsv_single(target_rgb)
            if target_hsv is None:
                return None
            
            h_target, s_target, v_target = target_hsv
            
            h_tolerance = min(30, tolerance * 0.5) 
            
            s_tolerance = tolerance * 1.2 if s_target < 100 else tolerance * 0.8
            
            v_tolerance = tolerance * 1.1
            
            h_low = (h_target - h_tolerance) % 180
            h_high = (h_target + h_tolerance) % 180
            
            if h_low <= h_high:
                h_mask = (img_hsv[:, :, 0] >= h_low) & (img_hsv[:, :, 0] <= h_high)
            else: 
                h_mask = (img_hsv[:, :, 0] >= h_low) | (img_hsv[:, :, 0] <= h_high)
            
            s_mask = (img_hsv[:, :, 1] >= max(0, s_target - s_tolerance)) & \
                     (img_hsv[:, :, 1] <= min(255, s_target + s_tolerance))
            
            v_mask = (img_hsv[:, :, 2] >= max(0, v_target - v_tolerance)) & \
                     (img_hsv[:, :, 2] <= min(255, v_target + v_tolerance))
            
            combined_mask = h_mask & s_mask & v_mask
            
            logger.debug(f"_create_hsv_color_mask: HSV target=({h_target}, {s_target}, {v_target}), tolerances=({h_tolerance}, {s_tolerance}, {v_tolerance})")
            return combined_mask
            
        except Exception as e:
            logger.debug(f"_create_hsv_color_mask: Exception: {e}")
            return None
    
    def _rgb_to_hsv_single(self, rgb):
        """Convert a single RGB color to HSV"""
        try:
            r, g, b = rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            diff = max_val - min_val
            
            v = max_val * 255
            
            s = 0 if max_val == 0 else (diff / max_val) * 255
            
            if diff == 0:
                h = 0
            elif max_val == r:
                h = (60 * ((g - b) / diff) + 360) % 360
            elif max_val == g:
                h = (60 * ((b - r) / diff) + 120) % 360
            else:
                h = (60 * ((r - g) / diff) + 240) % 360
            
            h = h / 2
            
            return (int(h), int(s), int(v))
        except Exception as e:
            logger.debug(f"_rgb_to_hsv_single: Exception: {e}")
            return None
    
    async def _ocr_single_image(self, image, image_name="unknown"):
        logger.debug(f"_ocr_single_image: Processing image with method '{image_name}', size: {image.size}")
        
        try:
            if not self.ocr_engine:
                logger.debug("_ocr_single_image: No OCR engine available")
                return ""
                
            img_byte_arr = io.BytesIO()
            if image.mode != 'RGB':
                logger.debug(f"_ocr_single_image: Converting image from {image.mode} to RGB")
                image = image.convert('RGB')
            image.save(img_byte_arr, format='PNG', optimize=False)
            img_bytes = img_byte_arr.getvalue()
            logger.debug(f"_ocr_single_image: Image converted to {len(img_bytes)} bytes")
            
            stream = InMemoryRandomAccessStream()
            data_writer = DataWriter(stream.get_output_stream_at(0))
            data_writer.write_bytes(img_bytes)
            
            await data_writer.store_async()
            decoder = await BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()
            ocr_result = await self.ocr_engine.recognize_async(software_bitmap)
            
            if ocr_result.text:
                full_text = ocr_result.text.strip()
                logger.debug(f"_ocr_single_image: Full OCR result: '{full_text}'")
                
                lines = full_text.split('\n')
                logger.debug(f"_ocr_single_image: OCR found {len(lines)} lines: {lines}")
                
                if lines:
                    bottom_line = self._select_bottom_rarity_line(lines)
                    logger.debug(f"_ocr_single_image: Selected bottom rarity line: '{bottom_line}'")
                    return bottom_line
            else:
                logger.debug("_ocr_single_image: OCR returned no text")
            
            return ""
            
        except Exception as e:
            logger.debug(f"_ocr_single_image: Exception occurred: {e}")
            return ""

    def _select_bottom_rarity_line(self, lines):
        """Select the bottom-most (newest) line that contains a rarity keyword"""
        logger.debug(f"_select_bottom_rarity_line: Processing {len(lines)} lines: {lines}")
        
        rarities = ['Junk', 'Common', 'Unusual', 'Scarce', 'Legendary', 'Mythical', 'Divine', 'Prismatic']
        
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line:  
                logger.debug(f"_select_bottom_rarity_line: Skipping empty line at position {i}")
                continue
                
            line_upper = line.upper()
            logger.debug(f"_select_bottom_rarity_line: Checking line {i}: '{line}'")
            
            for rarity in rarities:
                if rarity.upper() in line_upper:
                    logger.debug(f"_select_bottom_rarity_line: Found rarity '{rarity}' in bottom-most line {i}: '{line}'")
                    return line
        
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line:
                logger.debug(f"_select_bottom_rarity_line: No rarity found, returning bottom-most non-empty line: '{line}'")
                return line
        
        bottom_line = lines[-1] if lines else ""
        logger.debug(f"_select_bottom_rarity_line: All lines empty, returning original bottom: '{bottom_line}'")
        return bottom_line

    def test_item_ocr(self):
        logger.debug("test_item_ocr: Starting test")
        
        if not self.initialized or not self.item_area:
            logger.debug(f"test_item_ocr: Not ready - initialized: {self.initialized}, item_area: {self.item_area}")
            return None
        
        try:
            x, y, width, height = self.item_area
            logger.debug(f"test_item_ocr: Taking screenshot of area ({x}, {y}, {width}, {height})")
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            
            enhanced_images = self._enhance_for_rarity_colors(screenshot)
            logger.debug(f"test_item_ocr: Processing {len(enhanced_images)} enhanced images")
            
            for idx, (name, img) in enumerate(enhanced_images):
                logger.debug(f"test_item_ocr: Testing method {idx + 1}/{len(enhanced_images)}: '{name}'")
                
                try:
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    result = loop.run_until_complete(self._ocr_single_image(img, name))
                    logger.debug(f"test_item_ocr: OCR result from '{name}': '{result}'")
                    
                    if result and result.strip():
                        rarity = self.extract_rarity(result)
                        logger.debug(f"test_item_ocr: Extracted rarity: {rarity}")
                        if rarity:
                            cleaned_result = self.clean_item_text(result)
                            logger.info(f"Test Item OCR successful - Rarity: {rarity}, Text: {cleaned_result} (method: {name})")
                            logger.debug(f"test_item_ocr: Successful result found, closing loop and returning")
                            try:
                                loop.close()
                            except:
                                pass
                            return (rarity, cleaned_result)
                        else:
                            logger.info(f"Test Item OCR - Text found but no rarity: {result} (method: {name})")
                    else:
                        logger.debug(f"Test Item OCR - No text found with method: {name}")
                except Exception as e:
                    logger.debug(f"Test Item OCR method {name} failed: {e}")
                    continue
                    
                try:
                    loop.close()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Test Item OCR failed: {e}")
            return None
        
        logger.debug("test_item_ocr: All methods tested, no results found")
        return None
