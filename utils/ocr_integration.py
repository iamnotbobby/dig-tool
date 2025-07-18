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
    
    def read_money_value(self, max_retries=3, retry_delay=0.5):
        if not self.initialized or not self.money_area:
            return None
            
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import time
                    time.sleep(retry_delay)
                    logger.debug(f"Money OCR retry attempt {attempt + 1}/{max_retries}")
                
                x, y, width, height = self.money_area
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                
                enhanced_images = self._enhance_for_green_text(screenshot)
                
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
                            clean_text = self._clean_money_text(result)
                            if clean_text:
                                formatted_money = self._format_money_value(clean_text)
                                logger.info(f"Money detected: {formatted_money} (method: {name}, attempt: {attempt + 1})")
                                try:
                                    loop.close()
                                except:
                                    pass
                                return formatted_money
                    except Exception as e:
                        continue
                
                try:
                    loop.close()
                except:
                    pass
                
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
        
        try:
            green_ranges = [
                {'low': np.array([0, 150, 0]), 'high': np.array([100, 255, 100])},
                {'low': np.array([50, 200, 50]), 'high': np.array([150, 255, 150])},
                {'low': np.array([100, 200, 0]), 'high': np.array([200, 255, 100])},
                {'low': np.array([0, 200, 0]), 'high': np.array([150, 255, 50])},
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
                enhanced_images.append(("green_isolated", green_isolated))
                
                for scale in [2, 3]:
                    scaled_green = green_isolated.resize(
                        (green_isolated.width * scale, green_isolated.height * scale), 
                        Image.Resampling.LANCZOS
                    )
                    enhanced_images.append((f"green_isolated_scaled_{scale}x", scaled_green))
        except Exception:
            pass
        
        try:
            r, g, b = image.split()
            g_enhanced = ImageEnhance.Contrast(g).enhance(3.0)
            green_channel_enhanced = Image.merge('RGB', (r, g_enhanced, b))
            enhanced_images.append(("green_channel_enhanced", green_channel_enhanced))
            
            green_only = g_enhanced.convert('RGB')
            enhanced_images.append(("green_channel_only", green_only))
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
    
    def _clean_money_text(self, text):
        if not text:
            return None
            
        import re
        
        text = text.strip()
        text = text.replace('O', '0').replace('l', '1').replace('I', '1')
        text = re.sub(r'\$+', '$', text)
        
        money_patterns = [
            r'\$\s*[\d,]+\.?\d*[KMBkmb]?',
            r'\$[\d,]+\.?\d*[KMBkmb]?',
            r'[\d]+,[\d,]+\.?\d*[KMBkmb]?',
            r'[\d,]{4,}\.?\d*[KMBkmb]?',
            r'[\d,]+\.?\d*[KMBkmb]?',
            r'\$?[\d,]+\.?\d*',
            r'[\d,]+\.?\d*',
            r'\$?\d+',
            r'\d+',
            r'[\d\s,]+',
        ]
        
        for pattern in money_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result = matches[0]
                result = re.sub(r'[^\d,.$KMBkmb]', '', result)
                if any(c.isdigit() for c in result):
                    return result
        
        cleaned = re.sub(r'[^\d,.]', '', text)
        if cleaned and any(c.isdigit() for c in cleaned):
            return cleaned
            
        return None
    
    def _format_money_value(self, money_text):
        if not money_text:
            return money_text
            
        import re
        
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
