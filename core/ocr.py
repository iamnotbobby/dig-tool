import tkinter as tk
import asyncio
import time
from PIL import Image, ImageEnhance
import io
import pyautogui
import numpy as np
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter

from utils.debug_logger import logger


class BaseOCR:
    def __init__(self):
        self.ocr_engine = None
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
    
    def _get_async_loop(self):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

class AreaSelector:
    def __init__(self, color="#00ff88", area_type="Area"):
        self.color = color
        self.area_type = area_type
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
            highlightbackground=self.color,
            highlightcolor=self.color,
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
            x1, y1 = min(self.start_x or 0, self.end_x or 0), min(self.start_y or 0, self.end_y or 0)
            x2, y2 = max(self.start_x or 0, self.end_x or 0), max(self.start_y or 0, self.end_y or 0)
            result = (x1, y1, x2 - x1, y2 - y1)
            logger.info(f"{self.area_type} area selected: {x2-x1}x{y2-y1} at ({x1},{y1})")
            return result
        return None

class MoneyOCR(BaseOCR):
    def __init__(self):
        super().__init__()
        self.money_area = None
        
    def select_money_area(self):
        try:
            selector = AreaSelector("#00ff88", "Money")
            self.money_area = selector.select_area()
            return bool(self.money_area)
        except Exception as e:
            logger.error(f"Area selection failed: {e}")
            return False
    
    def read_money_value(self, max_retries=2, retry_delay=0.3):
        if not self.initialized or not self.money_area:
            return None
        
        x, y, width, height = self.money_area
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        return self._process_money_ocr(screenshot, max_retries, retry_delay)
    
    def read_money_from_screenshot(self, full_screenshot, max_retries=3, retry_delay=0.5):
        if not self.initialized or not self.money_area:
            return None
        
        x, y, width, height = self.money_area
        cropped_screenshot = full_screenshot.crop((x, y, x + width, y + height))
        return self._process_money_ocr(cropped_screenshot, max_retries, retry_delay)
    
    def test_money_ocr(self):
        if not self.initialized or not self.money_area:
            return None
        
        x, y, width, height = self.money_area
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        return self._process_money_ocr(screenshot, 1, 0)
    
    def _process_money_ocr(self, screenshot, max_retries, retry_delay):
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(retry_delay)
                    logger.debug(f"Money OCR retry {attempt + 1}/{max_retries}")
                
                enhanced_images = self._enhance_for_green_text(screenshot)
                
                priority_methods = ["original", "scaled_2x", "green_channel_3x"]
                
                for priority_name in priority_methods:
                    for name, img in enhanced_images:
                        if name == priority_name:
                            result = self._try_ocr_method(img, name)
                            if result:
                                return result
                            break
                
                for name, img in enhanced_images:
                    if name not in priority_methods:
                        result = self._try_ocr_method(img, name)
                        if result:
                            return result
                    
            except Exception as e:
                logger.error(f"Money OCR attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
        
        return None
    
    def _try_ocr_method(self, img, name):
        try:
            loop = self._get_async_loop()
            result = loop.run_until_complete(self._ocr_single_image(img, name))
            
            if result and result.strip():
                clean_text = self._clean_money_text(result)
                if clean_text:
                    formatted_money = self._format_money_value(clean_text)
                    logger.info(f"Money detected: {formatted_money} (method: {name})")
                    return formatted_money
            
        except Exception as e:
            logger.debug(f"OCR method '{name}' failed: {e}")
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

class ItemOCR(BaseOCR):
    def __init__(self):
        super().__init__()
        self.item_area = None
        
    def select_item_area(self):
        try:
            selector = AreaSelector("#4da6ff", "Item")
            self.item_area = selector.select_area()
            if self.item_area:
                logger.debug(f"Item area selected: {self.item_area}")
            return bool(self.item_area)
        except Exception as e:
            logger.error(f"Item area selection failed: {e}")
            return False
    
    def read_item_text(self, max_retries=2, retry_delay=0.3):
        if not self.initialized or not self.item_area:
            logger.debug(f"ItemOCR not ready - initialized: {self.initialized}, area: {bool(self.item_area)}")
            return None
        
        x, y, width, height = self.item_area
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        return self._process_item_ocr(screenshot, max_retries, retry_delay)
    
    def test_item_ocr(self):
        if not self.initialized or not self.item_area:
            logger.debug(f"ItemOCR test not ready - initialized: {self.initialized}, area: {bool(self.item_area)}")
            return None
        
        x, y, width, height = self.item_area
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        result = self._process_item_ocr(screenshot, 1, 0)
        
        if result:
            rarity = self.extract_rarity(result)
            if rarity:
                logger.info(f"Test Item OCR successful - Rarity: {rarity}, Text: {result}")
                return (rarity, result)
        
        logger.debug("Item OCR test found no results")
        return None
    
    def _process_item_ocr(self, screenshot, max_retries, retry_delay):
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(retry_delay)
                    logger.debug(f"Item OCR retry {attempt + 1}/{max_retries}")
                
                enhanced_images = self._enhance_for_rarity_colors(screenshot)
                
                for idx, (name, img) in enumerate(enhanced_images):
                    result = self._try_item_ocr_method(img, name, attempt + 1)
                    if result:
                        return result
                    
            except Exception as e:
                logger.error(f"Item OCR attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
        
        return None
    
    def _try_item_ocr_method(self, img, name, attempt):
        try:
            loop = self._get_async_loop()
            result = loop.run_until_complete(self._ocr_single_image(img, name))
            
            if result and result.strip():
                full_text = result.strip()
                lines = full_text.split('\n')
                if lines:
                    bottom_line = self._select_bottom_rarity_line(lines)
                    result = bottom_line
                
                rarity = self.extract_rarity(result)
                
                if rarity:
                    logger.info(f"Item detected: {rarity} (method: {name}, attempt: {attempt})")
                    cleaned_result = self.clean_item_text(result)
                    return cleaned_result
            
        except Exception as e:
            logger.debug(f"OCR method '{name}' failed: {e}")
        return None
    
    def extract_rarity(self, text):
        if not text:
            return None
        
        rarities = ['Junk', 'Common', 'Unusual', 'Scarce', 'Legendary', 'Mythical', 'Divine', 'Prismatic']
        text_upper = text.upper()
        
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
            return None
        
        found_rarities.sort(key=lambda x: x[0])
        
        if len(found_rarities) == 1:
            return found_rarities[0][1]
        elif len(found_rarities) >= 2:
            first_rarity = found_rarities[0][1]
            second_rarity = found_rarities[1][1]
            
            if first_rarity.upper() == second_rarity.upper():
                return second_rarity  # Return duplicate (stacking case)
            else:
                return second_rarity  # Return second (more recent)
        
        return found_rarities[0][1]
    
    def clean_item_text(self, text):
        if not text:
            return text
        
        cleaned = ' '.join(text.split())
        artifacts_to_remove = ['|', '_', '~', '`', '\x00', '\ufffd']
        for artifact in artifacts_to_remove:
            cleaned = cleaned.replace(artifact, '')
        
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        rarities = ['Junk', 'Common', 'Unusual', 'Scarce', 'Legendary', 'Mythical', 'Divine', 'Prismatic']
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
            
            target_rarity = None
            if len(found_rarities) == 1:
                target_rarity = found_rarities[0][1]
            elif len(found_rarities) >= 2:
                target_rarity = found_rarities[1][1]  # Use second for stacking logic
            
            if target_rarity:
                return target_rarity.title()
        
        return cleaned.title().strip()
    
    def _enhance_for_rarity_colors(self, image):
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        if image.size[0] < 10 or image.size[1] < 10:
            return [("original", image)]
        
        enhanced_images = []
        img_array = np.array(image)
        
        try:
            color_preserved_image = self._create_color_preserved_image(img_array)
            if color_preserved_image is not None:
                enhanced_images.append(("color_preserved", color_preserved_image))
                
                black_text_image = self._convert_colors_to_black(color_preserved_image)
                if black_text_image is not None:
                    enhanced_images.append(("color_preserved_black_text", black_text_image))
                
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
                        logger.debug(f"Failed to scale color preserved images: {e}")
        except Exception as e:
            logger.debug(f"Color preservation failed: {e}")
        
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
    
    def _create_color_preserved_image(self, img_array):
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
            
            for color_name, color_info in rarity_colors.items():
                target_rgb = np.array(color_info['rgb'])
                best_pixels = 0
                color_mask = None
                
                for tolerance in color_info['tolerances']:
                    color_diff = np.sqrt(np.sum((img_array - target_rgb) ** 2, axis=2))
                    rgb_mask = color_diff <= tolerance
                    rgb_pixels = np.sum(rgb_mask)
                    
                    hsv_pixels = 0
                    hsv_mask = None
                    if img_hsv is not None:
                        hsv_mask = self._create_hsv_color_mask(img_hsv, target_rgb, tolerance)
                        if hsv_mask is not None:
                            hsv_pixels = np.sum(hsv_mask)
                    
                    current_pixels = max(rgb_pixels, hsv_pixels)
                    
                    if current_pixels > best_pixels:
                        best_pixels = current_pixels
                        color_mask = hsv_mask if hsv_pixels > rgb_pixels and hsv_mask is not None else rgb_mask
                    
                    if current_pixels > 50:
                        break
                
                if best_pixels > 0 and color_mask is not None:
                    rarity_mask = rarity_mask | color_mask
                    total_rarity_pixels += best_pixels
            
            if total_rarity_pixels > 0:
                result = np.full_like(img_array, 255)
                result[rarity_mask] = img_array[rarity_mask]
                return Image.fromarray(result)
            else:
                return None
                
        except Exception as e:
            logger.debug(f"Color preservation failed: {e}")
            return None
    
    def _convert_colors_to_black(self, color_preserved_image):
        try:
            img_array = np.array(color_preserved_image)
            white_threshold = 250
            non_white_mask = np.any(img_array < white_threshold, axis=2)
            
            if np.sum(non_white_mask) > 0:
                result = np.full_like(img_array, 255)
                result[non_white_mask] = [0, 0, 0]
                return Image.fromarray(result)
            else:
                return None
                
        except Exception as e:
            logger.debug(f"Color to black conversion failed: {e}")
            return None
    
    def _convert_to_hsv_safe(self, img_array):
        try:
            import cv2
            img_bgr = img_array[:, :, ::-1]  
            img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            return img_hsv
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"OpenCV HSV conversion failed: {e}")
        
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
            
            return hsv_array
        except Exception as e:
            logger.debug(f"Manual HSV conversion failed: {e}")
            return None
    
    def _create_hsv_color_mask(self, img_hsv, target_rgb, tolerance):
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
            
            return h_mask & s_mask & v_mask
            
        except Exception as e:
            logger.debug(f"HSV color mask creation failed: {e}")
            return None
    
    def _rgb_to_hsv_single(self, rgb):
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
            logger.debug(f"RGB to HSV conversion failed: {e}")
            return None
    
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
            
            if ocr_result.text:
                full_text = ocr_result.text.strip()
                lines = full_text.split('\n')
                
                if lines:
                    bottom_line = self._select_bottom_rarity_line(lines)
                    return bottom_line
            
            return ""
            
        except Exception as e:
            logger.debug(f"OCR failed for {image_name}: {e}")
            return ""

    def _select_bottom_rarity_line(self, lines):
        rarities = ['Junk', 'Common', 'Unusual', 'Scarce', 'Legendary', 'Mythical', 'Divine', 'Prismatic']
        
        # Look for rarity keywords from bottom to top
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if not line:  
                continue
                
            line_upper = line.upper()
            for rarity in rarities:
                if rarity.upper() in line_upper:
                    return line
        
        # Return bottom-most non-empty line if no rarity found
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line:
                return line
        
        # Fallback to last line
        return lines[-1] if lines else ""
