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
        root.configure(bg='#FF69B4', cursor='crosshair')
        
        selection_rect = tk.Frame(
            root,
            highlightthickness=2,
            highlightbackground="#FFD700",
            highlightcolor="#FFD700",
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
        
    def initialize_ocr(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.ocr_engine = OcrEngine.try_create_from_user_profile_languages()
            self.initialized = bool(self.ocr_engine)
            return self.initialized
        except Exception as e:
            logger.error(f"Item OCR initialization failed: {e}")
            return False
    
    def select_item_area(self):
        try:
            selector = ItemAreaSelector()
            self.item_area = selector.select_area()
            return bool(self.item_area)
        except Exception as e:
            logger.error(f"Item area selection failed: {e}")
            return False
    
    def read_item_text(self, max_retries=2, retry_delay=0.3):
        if not self.initialized or not self.item_area:
            return None
            
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import time
                    time.sleep(retry_delay)
                
                x, y, width, height = self.item_area
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                
                enhanced_images = self._enhance_for_rarity_colors(screenshot)
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                for name, img in enhanced_images:
                    try:
                        result = loop.run_until_complete(self._ocr_single_image(img, name))
                        
                        if result and result.strip():
                            rarity = self.extract_rarity(result)
                            if rarity:
                                logger.info(f"Item detected: {rarity} (method: {name}, attempt: {attempt + 1})")
                                try:
                                    loop.close()
                                except:
                                    pass
                                return result
                    except Exception as e:
                        continue
                
                try:
                    loop.close()
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Item OCR attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
        
        return None
    
    def extract_rarity(self, text):
        if not text:
            return None
        
        rarities = ['Junk', 'Common', 'Unusual', 'Scarce', 'Legendary', 'Mythical', 'Divine', 'Prismatic']
        
        text_upper = text.upper()
        for rarity in rarities:
            if rarity.upper() in text_upper:
                return rarity
        
        return None
    
    def _enhance_for_rarity_colors(self, image):
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        if image.size[0] < 10 or image.size[1] < 10:
            return [("original", image)]
        
        enhanced_images = []
        img_array = np.array(image)
        
        import cv2
        try:
            hsv_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        except:
            hsv_array = img_array
            use_hsv = False
        else:
            use_hsv = True
        
        if use_hsv:
            color_ranges = {
                'legendary': [
                    {'low': np.array([5, 100, 100]), 'high': np.array([15, 255, 255])},
                    {'low': np.array([10, 80, 80]), 'high': np.array([25, 255, 255])},
                ],
                'divine': [
                    {'low': np.array([150, 100, 100]), 'high': np.array([179, 255, 255])},
                    {'low': np.array([0, 100, 100]), 'high': np.array([5, 255, 255])},
                    {'low': np.array([140, 80, 80]), 'high': np.array([160, 255, 255])},
                ],
                'mythical': [
                    {'low': np.array([140, 100, 100]), 'high': np.array([160, 255, 255])},
                    {'low': np.array([150, 80, 80]), 'high': np.array([170, 255, 255])},
                ],
                'prismatic': [
                    {'low': np.array([0, 100, 100]), 'high': np.array([15, 255, 255])},
                    {'low': np.array([15, 100, 100]), 'high': np.array([45, 255, 255])},
                    {'low': np.array([45, 100, 100]), 'high': np.array([75, 255, 255])},
                    {'low': np.array([75, 100, 100]), 'high': np.array([105, 255, 255])},
                    {'low': np.array([105, 100, 100]), 'high': np.array([135, 255, 255])},
                    {'low': np.array([135, 100, 100]), 'high': np.array([165, 255, 255])},
                    {'low': np.array([165, 100, 100]), 'high': np.array([179, 255, 255])},
                ],
                'scarce': [
                    {'low': np.array([100, 100, 100]), 'high': np.array([130, 255, 255])},
                    {'low': np.array([110, 80, 80]), 'high': np.array([140, 255, 255])},
                ]
            }
        else:
            color_ranges = {
                'legendary': [
                    {'low': np.array([150, 100, 0]), 'high': np.array([255, 220, 120])},
                    {'low': np.array([180, 120, 0]), 'high': np.array([255, 180, 80])},
                    {'low': np.array([200, 140, 20]), 'high': np.array([255, 200, 100])},
                ],
                'divine': [
                    {'low': np.array([180, 0, 100]), 'high': np.array([255, 120, 255])},
                    {'low': np.array([200, 20, 20]), 'high': np.array([255, 80, 80])},
                    {'low': np.array([150, 0, 150]), 'high': np.array([255, 100, 255])},
                ],
                'mythical': [
                    {'low': np.array([150, 0, 100]), 'high': np.array([255, 120, 220])},
                    {'low': np.array([180, 0, 120]), 'high': np.array([255, 80, 180])},
                    {'low': np.array([200, 80, 150]), 'high': np.array([255, 150, 200])},
                ],
                'prismatic': [
                    {'low': np.array([180, 0, 0]), 'high': np.array([255, 120, 120])},
                    {'low': np.array([150, 150, 0]), 'high': np.array([255, 255, 120])},
                    {'low': np.array([0, 150, 0]), 'high': np.array([120, 255, 120])},
                    {'low': np.array([0, 150, 150]), 'high': np.array([120, 255, 255])},
                    {'low': np.array([0, 0, 150]), 'high': np.array([120, 120, 255])},
                    {'low': np.array([150, 0, 150]), 'high': np.array([255, 120, 255])},
                    {'low': np.array([200, 100, 120]), 'high': np.array([255, 170, 180])},
                    {'low': np.array([220, 130, 125]), 'high': np.array([255, 210, 195])},
                    {'low': np.array([180, 220, 100]), 'high': np.array([260, 255, 170])},
                    {'low': np.array([140, 220, 140]), 'high': np.array([210, 255, 210])},
                ],
                'scarce': [
                    {'low': np.array([0, 80, 150]), 'high': np.array([120, 180, 255])},
                    {'low': np.array([80, 60, 180]), 'high': np.array([160, 140, 250])},
                    {'low': np.array([100, 80, 200]), 'high': np.array([160, 130, 240])},
                ]
            }
        
        try:
            for rarity_name, ranges in color_ranges.items():
                mask = np.zeros(img_array.shape[:2], dtype=bool)
                
                for range_def in ranges:
                    if use_hsv:
                        low_h, low_s, low_v = range_def['low']
                        high_h, high_s, high_v = range_def['high']
                        
                        if low_h > high_h:
                            mask1 = np.all((hsv_array >= [low_h, low_s, low_v]) & (hsv_array <= [179, 255, 255]), axis=2)
                            mask2 = np.all((hsv_array >= [0, low_s, low_v]) & (hsv_array <= [high_h, high_s, high_v]), axis=2)
                            color_mask = mask1 | mask2
                        else:
                            color_mask = np.all((hsv_array >= range_def['low']) & (hsv_array <= range_def['high']), axis=2)
                    else:
                        color_mask = np.all((img_array >= range_def['low']) & (img_array <= range_def['high']), axis=2)
                    
                    mask = mask | color_mask
                
                if np.any(mask):
                    result = np.zeros_like(img_array)
                    result[mask] = [255, 255, 255]
                    result[~mask] = [0, 0, 0]
                    isolated_image = Image.fromarray(result)
                    enhanced_images.append((f"{rarity_name}_isolated", isolated_image))
                    
                    for scale in [2, 3]:
                        scaled = isolated_image.resize(
                            (isolated_image.width * scale, isolated_image.height * scale), 
                            Image.Resampling.LANCZOS
                        )
                        enhanced_images.append((f"{rarity_name}_isolated_scaled_{scale}x", scaled))
        except Exception:
            pass
        
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

    def test_item_ocr(self):
        if not self.initialized or not self.item_area:
            return None
        
        try:
            x, y, width, height = self.item_area
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            
            enhanced_images = self._enhance_for_rarity_colors(screenshot)
            
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
                        rarity = self.extract_rarity(result)
                        if rarity:
                            logger.info(f"Test Item OCR successful - Rarity: {rarity}, Text: {result} (method: {name})")
                            return (rarity, result)
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
        
        return None
