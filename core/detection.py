import numpy as np
import collections
import cv2


def detect_by_saturation(hsv, saturation_threshold):
    saturation = hsv[:, :, 1]
    _, mask = cv2.threshold(saturation, saturation_threshold, 255, cv2.THRESH_BINARY)
    return mask


def detect_by_otsu_with_area_filter(
    hsv, min_area=50, max_area=None, morph_kernel_size=3
):
    """
    Alternative detection method using Otsu's thresholding with area filtering.

    Args:
        hsv: HSV image array
        min_area: Minimum contour area to keep (default: 50)
        max_area: Maximum contour area to keep (None for no upper limit)
        morph_kernel_size: Size of morphological operations kernel (default: 3)

    Returns:
        Binary mask with detected regions
    """
    # Extract saturation channel
    saturation = hsv[:, :, 1]

    # Apply Otsu's thresholding
    threshold_value, otsu_mask = cv2.threshold(
        saturation, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Optional: Apply morphological operations to clean up the mask
    if morph_kernel_size > 0:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size)
        )
        # Close small gaps
        otsu_mask = cv2.morphologyEx(otsu_mask, cv2.MORPH_CLOSE, kernel)
        # Remove small noise
        otsu_mask = cv2.morphologyEx(otsu_mask, cv2.MORPH_OPEN, kernel)

    # Apply area filtering
    if min_area > 0 or max_area is not None:
        # Find contours
        contours, _ = cv2.findContours(
            otsu_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Create a new mask for filtered contours
        filtered_mask = np.zeros_like(otsu_mask)

        for contour in contours:
            area = cv2.contourArea(contour)

            # Check area constraints
            if area >= min_area:
                if max_area is None or area <= max_area:
                    # Fill the contour in the filtered mask
                    cv2.fillPoly(filtered_mask, [contour], 255)

        return filtered_mask, threshold_value

    return otsu_mask, threshold_value


def detect_by_otsu_adaptive_area(hsv, area_percentile=0.1, morph_kernel_size=3):
    """
    Otsu detection with adaptive area filtering based on image size.

    Args:
        hsv: HSV image array
        area_percentile: Minimum area as percentage of image size (default: 0.1%)
        morph_kernel_size: Size of morphological operations kernel

    Returns:
        Binary mask with detected regions and threshold value
    """
    height, width = hsv.shape[:2]
    image_area = height * width
    min_area = int(image_area * (area_percentile / 100.0))

    return detect_by_otsu_with_area_filter(
        hsv, min_area=min_area, morph_kernel_size=morph_kernel_size
    )


def get_hsv_bounds(hsv_color, is_low_sat):
    if is_low_sat:
        v_range = 40
        lower_bound = np.array([0, 0, max(0, hsv_color[2] - v_range)], dtype=np.uint8)
        upper_bound = np.array(
            [179, 50, min(255, hsv_color[2] + v_range)], dtype=np.uint8
        )
    else:
        h_range, s_range, v_range = 10, 70, 70
        lower_bound = np.array(
            [
                max(0, hsv_color[0] - h_range),
                max(0, hsv_color[1] - s_range),
                max(0, hsv_color[2] - v_range),
            ],
            dtype=np.uint8,
        )
        upper_bound = np.array(
            [
                min(179, hsv_color[0] + h_range),
                min(255, hsv_color[1] + s_range),
                min(255, hsv_color[2] + v_range),
            ],
            dtype=np.uint8,
        )
    return lower_bound, upper_bound


def apply_line_exclusion(mask, cursor_pos, game_area, line_exclusion_radius):
    if line_exclusion_radius <= 0:
        return mask
    try:
        cursor_x, cursor_y = cursor_pos
        x, y, w, h = game_area
        relative_cursor_x = cursor_x - x
        relative_cursor_y = cursor_y - y
        if 0 <= relative_cursor_x < w and 0 <= relative_cursor_y < h:
            cv2.circle(
                mask,
                (relative_cursor_x, relative_cursor_y),
                line_exclusion_radius,
                0,
                -1,
            )
    except:
        pass
    return mask


def find_line_position(
    gray_array, sensitivity_threshold=50, min_height_ratio=0.7, offset=0
):
    height, width = gray_array.shape
    if width < 3:
        return -1
    thresh = sensitivity_threshold * height * 0.2
    strong_edge_threshold = sensitivity_threshold * 0.5
    min_pixels = height * min_height_ratio
    left_right_diff = np.abs(
        gray_array[:, 2:].astype(np.float32) - gray_array[:, :-2].astype(np.float32)
    )
    center_left_diff = np.abs(
        gray_array[:, 1:-1].astype(np.float32) - gray_array[:, :-2].astype(np.float32)
    )
    gradients = left_right_diff + center_left_diff
    vertical_sum = np.sum(gradients, axis=0)
    strong_pixel_count = np.sum(gradients > strong_edge_threshold, axis=0)
    valid_mask = (vertical_sum > thresh) & (strong_pixel_count >= min_pixels)
    if not np.any(valid_mask):
        return -1
    best_idx = np.argmax(vertical_sum * valid_mask)
    detected_position = best_idx + 1
    if offset is None:
        offset = 0.0
    final_position = detected_position + float(offset)
    final_position = int(round(final_position))
    return max(0, min(final_position, width - 1))


class VelocityCalculator:
    def __init__(self, history_length=12):
        self.position_history = collections.deque(maxlen=history_length)
        self.velocity_history = collections.deque(maxlen=6)
        self._smoothing_weights = np.array([0.15, 0.25, 0.35, 0.25], dtype=np.float32)
        self._time_interval = 1.0 / 120.0
        self._fps = 120.0
        self._adaptive_history_length = history_length

    def update_fps(self, fps):
        self._fps = max(fps, 1.0)
        self._time_interval = 1.0 / self._fps
        new_history_length = max(int(12 * (self._fps / 60.0)), 6)
        if new_history_length != self._adaptive_history_length:
            self._adaptive_history_length = new_history_length
            new_position_history = collections.deque(maxlen=new_history_length)
            new_position_history.extend(
                list(self.position_history)[-new_history_length:]
            )
            self.position_history = new_position_history
            new_velocity_length = max(int(6 * (self._fps / 60.0)), 4)
            new_velocity_history = collections.deque(maxlen=new_velocity_length)
            new_velocity_history.extend(
                list(self.velocity_history)[-new_velocity_length:]
            )
            self.velocity_history = new_velocity_history

    def add_position(self, position, timestamp):
        if position == -1:
            return 0
        self.position_history.append((position, timestamp))
        return self.calculate_velocity()

    def calculate_velocity(self):
        hist_len = len(self.position_history)
        if hist_len < 2:
            return 0
        valid_points = [(pos, t) for pos, t in self.position_history if pos != -1]
        valid_len = len(valid_points)
        if valid_len < 2:
            return 0
        fps_scale = self._fps / 120.0
        min_samples_needed = max(int(2 * fps_scale), 2)
        if valid_len >= min_samples_needed and valid_len >= 3:
            velocity = self._fps_aware_velocity_calculation(valid_points)
        else:
            pos1, t1 = valid_points[-2]
            pos2, t2 = valid_points[-1]
            dt = t2 - t1
            velocity = (pos2 - pos1) / dt if dt > 0 else 0
        velocity = self._apply_fps_smoothing(velocity)
        self.velocity_history.append(velocity)
        return self._smooth_velocity_optimized()

    def _fps_aware_velocity_calculation(self, points):
        points_len = len(points)
        if points_len < 3:
            return 0
        positions = np.array([pos for pos, _ in points], dtype=np.float64)
        timestamps = np.array([t for _, t in points], dtype=np.float64)

        timestamps = timestamps - timestamps[0]

        pos_diffs = np.diff(positions)
        time_diffs = np.diff(timestamps)
        valid_times = time_diffs > 1e-6
        if not np.any(valid_times):
            return 0
        velocities = np.divide(
            pos_diffs, time_diffs, out=np.zeros_like(pos_diffs), where=valid_times
        )
        velocities = velocities[valid_times]
        if len(velocities) == 0:
            return 0
        if len(velocities) == 1:
            return velocities[0]
        fps_factor = min(self._fps / 60.0, 2.0)
        noise_filter_threshold = 10.0 / fps_factor
        filtered_velocities = velocities[np.abs(velocities) < 20000]
        if len(filtered_velocities) == 0:
            filtered_velocities = velocities
        vel_len = len(filtered_velocities)
        time_weight_factor = min(fps_factor, 1.5)
        exp_weights = np.exp(np.linspace(-1 * time_weight_factor, 0, vel_len))
        exp_weights /= np.sum(exp_weights)
        return float(np.dot(filtered_velocities, exp_weights))

    def _apply_fps_smoothing(self, velocity):
        if self._fps < 60:
            smoothing_factor = 0.2
        elif self._fps < 120:
            smoothing_factor = 0.3
        else:
            smoothing_factor = 0.4
        if len(self.velocity_history) > 0:
            last_velocity = self.velocity_history[-1]
            return smoothing_factor * velocity + (1 - smoothing_factor) * last_velocity
        return velocity

    def _smooth_velocity_optimized(self):
        hist_len = len(self.velocity_history)
        if hist_len == 0:
            return 0
        if hist_len == 1:
            return self.velocity_history[-1]
        fps_factor = self._fps / 120.0
        weights_count = min(hist_len, len(self._smoothing_weights))
        weights = self._smoothing_weights[-weights_count:]
        if fps_factor < 0.5:
            weights = weights**0.8
        elif fps_factor > 1.5:
            weights = weights**1.2
        weights = weights / np.sum(weights)
        velocities = np.array(
            list(self.velocity_history)[-weights_count:], dtype=np.float32
        )
        return np.dot(velocities, weights)

    def get_acceleration(self):
        hist_len = len(self.velocity_history)
        if hist_len < 2:
            return 0
        fps_factor = self._fps / 120.0
        sample_count = max(int(3 * fps_factor), 2)
        sample_count = min(sample_count, hist_len)
        recent_velocities = np.array(
            list(self.velocity_history)[-sample_count:], dtype=np.float32
        )
        if len(recent_velocities) < 2:
            return 0
        time_span = self._time_interval * (len(recent_velocities) - 1)
        acceleration = (recent_velocities[-1] - recent_velocities[0]) / time_span
        acceleration_limit = 50000 * fps_factor
        return np.clip(acceleration, -acceleration_limit, acceleration_limit)

    def predict_position(self, current_pos, target_pos, current_time):
        if len(self.velocity_history) == 0:
            return current_pos, 0.0
        velocity = self.velocity_history[-1]
        acceleration = self.get_acceleration()
        fps_factor = self._fps / 120.0
        if fps_factor < 0.5:
            acceleration_weight = 0.3
            velocity_smoothing = 0.8
        elif fps_factor > 1.5:
            acceleration_weight = 0.7
            velocity_smoothing = 0.95
        else:
            acceleration_weight = 0.5
            velocity_smoothing = 0.9
        if len(self.velocity_history) >= 2:
            velocity = (
                velocity_smoothing * velocity
                + (1 - velocity_smoothing) * self.velocity_history[-2]
            )
        if abs(velocity) < 1.0:
            return current_pos, 0.0
        distance_to_target = target_pos - current_pos
        if (distance_to_target > 0 and velocity <= 0) or (
            distance_to_target < 0 and velocity >= 0
        ):
            return current_pos, 0.0
        prediction_time = self._calculate_optimal_prediction_time(
            current_pos, target_pos, velocity, acceleration
        )
        if prediction_time <= 0:
            return current_pos, 0.0
        base_prediction = current_pos + (velocity * prediction_time)
        acceleration_component = (
            acceleration_weight * acceleration * prediction_time * prediction_time * 0.5
        )
        predicted_pos = base_prediction + acceleration_component
        max_movement = abs(velocity) * prediction_time * 2.0
        movement_limit = (
            current_pos + np.sign(velocity) * max_movement
            if velocity != 0
            else current_pos
        )
        if velocity > 0:
            predicted_pos = min(predicted_pos, movement_limit)
        elif velocity < 0:
            predicted_pos = max(predicted_pos, movement_limit)
        return predicted_pos, prediction_time

    def _calculate_optimal_prediction_time(
        self, current_pos, target_pos, velocity, acceleration
    ):
        distance_to_target = target_pos - current_pos
        fps_factor = self._fps / 120.0
        base_max_time = 0.5 * fps_factor
        min_time = 0.005
        if abs(velocity) < 10:
            return 0.0
        basic_time_to_target = distance_to_target / velocity if velocity != 0 else 0.0
        if basic_time_to_target <= 0 or basic_time_to_target > base_max_time:
            return 0.0
        if abs(acceleration) > 1000:
            a = 0.5 * acceleration
            b = velocity
            c = current_pos - target_pos
            discriminant = b * b - 4 * a * c
            if discriminant >= 0:
                sqrt_discriminant = np.sqrt(discriminant)
                t1 = (-b + sqrt_discriminant) / (2 * a) if a != 0 else 0
                t2 = (-b - sqrt_discriminant) / (2 * a) if a != 0 else 0
                valid_times = [t for t in [t1, t2] if min_time <= t <= base_max_time]
                if valid_times:
                    return min(valid_times)
        optimal_time = min(basic_time_to_target, base_max_time)
        return max(optimal_time, min_time) if optimal_time > min_time else 0.0

    def get_prediction_confidence(
        self, current_pos, target_pos, predicted_pos, prediction_time, fps
    ):
        if len(self.velocity_history) < 2 or prediction_time <= 0:
            return 0.0
        velocity_consistency = self._calculate_velocity_consistency()
        distance_factor = self._calculate_distance_factor(
            current_pos, target_pos, predicted_pos
        )
        fps_confidence = self._calculate_fps_confidence(fps)
        time_factor = self._calculate_time_factor(prediction_time)
        return velocity_consistency * distance_factor * fps_confidence * time_factor

    def _calculate_time_factor(self, prediction_time):
        if prediction_time <= 0:
            return 0.0
        elif prediction_time <= 0.05:
            return 1.0
        elif prediction_time <= 0.1:
            return 1.0 - (prediction_time - 0.05) / 0.05 * 0.2
        elif prediction_time <= 0.2:
            return 0.8 - (prediction_time - 0.1) / 0.1 * 0.3
        else:
            return max(0.1, 0.5 - (prediction_time - 0.2) * 2.0)

    def _calculate_velocity_consistency(self):
        if len(self.velocity_history) < 3:
            return 0.7
        recent_velocities = np.array(list(self.velocity_history)[-3:])
        velocity_std = np.std(recent_velocities)
        velocity_mean = np.abs(np.mean(recent_velocities))
        if velocity_mean == 0:
            return 0.0
        normalized_std = velocity_std / velocity_mean
        consistency = 1.0 / (1.0 + normalized_std * 0.5)
        return min(max(consistency, 0.4), 1.0)

    def _calculate_distance_factor(self, current_pos, target_pos, predicted_pos):
        current_distance = abs(current_pos - target_pos)
        predicted_distance = abs(predicted_pos - target_pos)
        if current_distance == 0:
            return 1.0 if predicted_distance == 0 else 0.7
        improvement_ratio = (current_distance - predicted_distance) / current_distance
        distance_factor = max(0.3, min(1.0, improvement_ratio + 0.6))
        return distance_factor

    def _calculate_fps_confidence(self, fps):
        if fps >= 120:
            return 1.0
        elif fps >= 60:
            return 0.85 + 0.15 * (fps - 60) / 60
        elif fps >= 30:
            return 0.6 + 0.25 * (fps - 30) / 30
        else:
            return 0.3 + 0.3 * fps / 30

    def reset(self):
        self.position_history.clear()
        self.velocity_history.clear()


def calculate_velocity_based_sweet_spot_width(
    base_width_percent,
    velocity,
    enabled=True,
    velocity_multiplier=1.5,
    max_velocity_factor=500.0,
):
    """
    Calculate dynamic sweet spot width based on velocity.
    Higher velocity = wider sweet spot for easier targeting.

    Args:
        base_width_percent: Base sweet spot width percentage
        velocity: Current line velocity in pixels/second
        enabled: Whether the feature is enabled
        velocity_multiplier: How much velocity affects the width (0.0-5.0)
        max_velocity_factor: Maximum velocity for normalization (default: 500.0)

    Returns:
        Dynamic sweet spot width percentage
    """
    if not enabled or velocity_multiplier <= 0:
        return base_width_percent

    normalized_velocity = min(abs(velocity) / max_velocity_factor, 1.0)

    # Calculate dynamic width using extrapolation formula
    # At velocity 0: use base width
    # At max velocity: use base width * (1 + velocity_multiplier)
    dynamic_width_percent = base_width_percent * (
        1.0 + normalized_velocity * velocity_multiplier
    )

    # Clamp the result to reasonable bounds (5% to 50% of zone width)
    return max(5.0, min(50.0, dynamic_width_percent))


def detect_by_color_picker(hsv, target_color_hsv, color_tolerance=30):
    """
    Detection method using a user-picked color with tolerance.

    Args:
        hsv: HSV image array
        target_color_hsv: Target color in HSV format [H, S, V]
        color_tolerance: Tolerance for color matching (default: 30)

    Returns:
        Binary mask with detected regions matching the target color
    """
    # Create mask for the target color with tolerance
    lower_bound = np.array(
        [
            max(0, target_color_hsv[0] - color_tolerance),
            max(0, target_color_hsv[1] - color_tolerance),
            max(0, target_color_hsv[2] - color_tolerance),
        ],
        dtype=np.uint8,
    )

    upper_bound = np.array(
        [
            min(179, target_color_hsv[0] + color_tolerance),
            min(255, target_color_hsv[1] + color_tolerance),
            min(255, target_color_hsv[2] + color_tolerance),
        ],
        dtype=np.uint8,
    )

    # Handle hue wraparound (red color case)
    if target_color_hsv[0] - color_tolerance < 0:
        # Split into two ranges for hue wraparound
        mask1 = cv2.inRange(
            hsv,
            np.array([0, lower_bound[1], lower_bound[2]], dtype=np.uint8),
            np.array(
                [target_color_hsv[0] + color_tolerance, upper_bound[1], upper_bound[2]],
                dtype=np.uint8,
            ),
        )
        mask2 = cv2.inRange(
            hsv,
            np.array(
                [
                    180 + target_color_hsv[0] - color_tolerance,
                    lower_bound[1],
                    lower_bound[2],
                ],
                dtype=np.uint8,
            ),
            np.array([179, upper_bound[1], upper_bound[2]], dtype=np.uint8),
        )
        mask = cv2.bitwise_or(mask1, mask2)
    elif target_color_hsv[0] + color_tolerance > 179:
        # Split into two ranges for hue wraparound
        mask1 = cv2.inRange(
            hsv,
            np.array([lower_bound[0], lower_bound[1], lower_bound[2]], dtype=np.uint8),
            np.array([179, upper_bound[1], upper_bound[2]], dtype=np.uint8),
        )
        mask2 = cv2.inRange(
            hsv,
            np.array([0, lower_bound[1], lower_bound[2]], dtype=np.uint8),
            np.array(
                [
                    target_color_hsv[0] + color_tolerance - 180,
                    upper_bound[1],
                    upper_bound[2],
                ],
                dtype=np.uint8,
            ),
        )
        mask = cv2.bitwise_or(mask1, mask2)
    else:
        # Normal case - no hue wraparound
        mask = cv2.inRange(hsv, lower_bound, upper_bound)

    return mask


def rgb_to_hsv_single(rgb_color):
    """
    Convert a single RGB color to HSV format for OpenCV.

    Args:
        rgb_color: RGB color as [R, G, B] or 0xRRGGBB format

    Returns:
        HSV color as [H, S, V] in OpenCV format (H: 0-179, S: 0-255, V: 0-255)
    """
    if isinstance(rgb_color, int):
        # Convert from 0xRRGGBB format
        r = (rgb_color >> 16) & 0xFF
        g = (rgb_color >> 8) & 0xFF
        b = rgb_color & 0xFF
    else:
        # Assume it's already [R, G, B]
        r, g, b = rgb_color

    # Create a 1x1 RGB image
    rgb_array = np.array([[[b, g, r]]], dtype=np.uint8)
    hsv_array = cv2.cvtColor(rgb_array, cv2.COLOR_BGR2HSV)

    return hsv_array[0, 0]
