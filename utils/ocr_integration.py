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
                                        self._save_success_debug_images(screenshot, enhanced_images, attempt + 1, debug_ocr_results, name, result, formatted_money)
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
                                    # self._save_success_debug_images(screenshot, enhanced_images, attempt + 1, debug_ocr_results, name, result, formatted_money)
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
                    # self._save_debug_images(screenshot, enhanced_images, attempt + 1, debug_ocr_results)
                    return None
        
        logger.warning("No money value detected after all retry attempts")
        # self._save_debug_images(screenshot, enhanced_images, max_retries, debug_ocr_results)
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
                                    # self._save_success_debug_images(cropped_screenshot, enhanced_images, attempt + 1, debug_ocr_results, name, result, formatted_money)
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
                                # self._save_success_debug_images(cropped_screenshot, enhanced_images, attempt + 1, debug_ocr_results, name, result, formatted_money)
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
                    # self._save_debug_images(cropped_screenshot, enhanced_images, attempt + 1, debug_ocr_results)
                    return None
        
        logger.warning("No money value detected after all retry attempts")
        # self._save_debug_images(cropped_screenshot, enhanced_images, max_retries, debug_ocr_results)
        return None
    
    def get_debug_info(self):
        return []
    
    def _save_debug_images(self, original_screenshot, enhanced_images, final_attempt, debug_ocr_results):
        pass
        # try:
        #     import os
        #     from datetime import datetime
        #     
        #     debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug", "ocr_failures")
        #     if not os.path.exists(debug_dir):
        #         os.makedirs(debug_dir, exist_ok=True)
        #     
        #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        #     failure_dir = os.path.join(debug_dir, f"failure_{timestamp}")
        #     os.makedirs(failure_dir, exist_ok=True)
        #     
        #     original_screenshot.save(os.path.join(failure_dir, "01_original_screenshot.png"))
        #     
        #     info_file = os.path.join(failure_dir, "debug_info.txt")
        #     with open(info_file, 'w') as f:
        #         f.write(f"OCR Failure Debug Information\n")
        #         f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        #         f.write(f"Final Attempt: {final_attempt}\n")
        #         f.write(f"Money Area: {self.money_area}\n")
        #         f.write(f"Original Image Size: {original_screenshot.size}\n\n")
        #         
        #         f.write(f"Enhancement Methods and Results:\n")
        #         for i, (name, img) in enumerate(enhanced_images, 2):
        #             f.write(f"  {i:02d}. {name} (size: {img.size})\n")
        #             img.save(os.path.join(failure_dir, f"{i:02d}_{name}.png"))
        #         
        #         f.write(f"\nOCR Results by Attempt:\n")
        #         for attempt_num, attempt_results in debug_ocr_results:
        #             f.write(f"\nAttempt {attempt_num}:\n")
        #             for method_name, ocr_result in attempt_results:
        #                 if ocr_result:
        #                     f.write(f"  {method_name}: '{ocr_result}'\n")
        #                 else:
        #                     f.write(f"  {method_name}: (no text detected)\n")
        #     
        #     logger.info(f"Debug images saved to: {failure_dir}")
        #     
        # except Exception as e:
        #     logger.error(f"Failed to save debug images: {e}")

    def _save_success_debug_images(self, original_screenshot, enhanced_images, attempt_num, debug_ocr_results, successful_method, ocr_text, formatted_money):
        # Debug image saving disabled
        pass
        # try:
        #     import os
        #     from datetime import datetime
        #     
        #     debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug", "ocr_successes")
        #     if not os.path.exists(debug_dir):
        #         os.makedirs(debug_dir, exist_ok=True)
        #     
        #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        #     success_dir = os.path.join(debug_dir, f"success_{timestamp}")
        #     os.makedirs(success_dir, exist_ok=True)
        #     
        #     original_screenshot.save(os.path.join(success_dir, "01_original_screenshot.png"))
        #     
        #     successful_img = None
        #     for name, img in enhanced_images:
        #         if name == successful_method:
        #             successful_img = img
        #             img.save(os.path.join(success_dir, f"99_SUCCESSFUL_{name}.png"))
        #             break
        #     
        #     info_file = os.path.join(success_dir, "debug_info.txt")
        #     with open(info_file, 'w') as f:
        #         f.write(f"OCR Success Debug Information\n")
        #         f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        #         f.write(f"Success on Attempt: {attempt_num}\n")
        #         f.write(f"Successful Method: {successful_method}\n")
        #         f.write(f"OCR Text Detected: '{ocr_text}'\n")
        #         f.write(f"Formatted Money: {formatted_money}\n")
        #         f.write(f"Money Area: {self.money_area}\n")
        #         f.write(f"Original Image Size: {original_screenshot.size}\n\n")
        #         
        #         if successful_img:
        #             f.write(f"Successful Image Size: {successful_img.size}\n\n")
        #         
        #         f.write(f"All Enhancement Methods Tried:\n")
        #         for i, (name, img) in enumerate(enhanced_images, 2):
        #             status = " *** SUCCESSFUL ***" if name == successful_method else ""
        #             f.write(f"  {i:02d}. {name} (size: {img.size}){status}\n")
        #             if name != successful_method:
        #                 img.save(os.path.join(success_dir, f"{i:02d}_{name}.png"))
        #         
        #         f.write(f"\nOCR Results by Attempt (up to success):\n")
        #         for attempt_num_debug, attempt_results in debug_ocr_results:
        #             f.write(f"\nAttempt {attempt_num_debug}:\n")
        #             for method_name, ocr_result in attempt_results:
        #                 if ocr_result:
        #                     status = " *** SUCCESS ***" if method_name == successful_method and attempt_num_debug == attempt_num else ""
        #                     f.write(f"  {method_name}: '{ocr_result}'{status}\n")
        #                 else:
        #                     f.write(f"  {method_name}: (no text detected)\n")
        #     
        #     logger.info(f"Success debug images saved to: {success_dir}")
        #     
        # except Exception as e:
        #     logger.error(f"Failed to save success debug images: {e}")
    
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
            
            result_text = ocr_result.text if ocr_result.text else ""
            
            return result_text
            
        except Exception as e:
            logger.error(f"OCR processing failed for {image_name}: {e}")
            return ""
    
    def _clean_money_text(self, text):
        if not text:
            return None
            
        import re
        
        text = text.strip()
        text = text.replace('O', '0').replace('l', '1').replace('I', '1')
        text = re.sub(r'\$+', '$', text)
        
        digits_only = re.sub(r'[^\d]', '', text)
        
        if not digits_only or len(digits_only) == 0:
            return None
            
        return digits_only
    
    def _format_money_value(self, money_text):
        if not money_text:
            return money_text
            
        import re
        
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
