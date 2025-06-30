import numpy as np
import collections


def find_line_position(gray_array, sensitivity_threshold=50, min_height_ratio=0.7):
    height, width = gray_array.shape
    if width < 3:
        return -1

    thresh = sensitivity_threshold * height * 0.2
    strong_edge_threshold = sensitivity_threshold * 0.5
    min_pixels = height * min_height_ratio

    left_right_diff = np.abs(gray_array[:, 2:].astype(np.float32) - gray_array[:, :-2].astype(np.float32))
    center_left_diff = np.abs(gray_array[:, 1:-1].astype(np.float32) - gray_array[:, :-2].astype(np.float32))
    gradients = left_right_diff + center_left_diff

    vertical_sum = np.sum(gradients, axis=0)
    strong_pixel_count = np.sum(gradients > strong_edge_threshold, axis=0)

    valid_mask = (vertical_sum > thresh) & (strong_pixel_count >= min_pixels)

    if not np.any(valid_mask):
        return -1

    best_idx = np.argmax(vertical_sum * valid_mask)
    return best_idx + 1


class VelocityCalculator:
    def __init__(self, history_length=10):
        self.position_history = collections.deque(maxlen=history_length)
        self.velocity_history = collections.deque(maxlen=5)

        self._smoothing_weights = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        self._time_interval = 1.0 / 120.0

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

        if valid_len >= 3:
            velocity = self._weighted_velocity_optimized(valid_points)
        else:
            pos1, t1 = valid_points[-2]
            pos2, t2 = valid_points[-1]
            dt = t2 - t1
            velocity = (pos2 - pos1) / dt if dt > 0 else 0

        self.velocity_history.append(velocity)
        return self._smooth_velocity_optimized()

    def _weighted_velocity_optimized(self, points):
        points_len = len(points)
        if points_len < 3:
            return 0

        positions = np.array([pos for pos, _ in points], dtype=np.float32)
        timestamps = np.array([t for _, t in points], dtype=np.float32)

        pos_diffs = np.diff(positions)
        time_diffs = np.diff(timestamps)

        valid_times = time_diffs > 0
        if not np.any(valid_times):
            return 0

        velocities = np.divide(pos_diffs, time_diffs, out=np.zeros_like(pos_diffs), where=valid_times)
        velocities = velocities[valid_times]

        if len(velocities) == 0:
            return 0
        if len(velocities) == 1:
            return velocities[0]

        vel_len = len(velocities)
        exp_weights = np.exp(np.linspace(-1, 0, vel_len))
        exp_weights /= np.sum(exp_weights)

        return np.dot(velocities, exp_weights)

    def _smooth_velocity_optimized(self):
        hist_len = len(self.velocity_history)
        if hist_len == 0:
            return 0
        if hist_len == 1:
            return self.velocity_history[-1]

        weights = self._smoothing_weights[-hist_len:]
        weights = weights / np.sum(weights)

        velocities = np.array(list(self.velocity_history), dtype=np.float32)
        return np.dot(velocities, weights)

    def get_acceleration(self):
        hist_len = len(self.velocity_history)
        if hist_len < 2:
            return 0

        recent_velocities = np.array(list(self.velocity_history)[-3:], dtype=np.float32)
        if len(recent_velocities) < 2:
            return 0

        return (recent_velocities[-1] - recent_velocities[0]) / (self._time_interval * (len(recent_velocities) - 1))

    def predict_position(self, current_pos, target_pos, current_time, prediction_time):
        if len(self.velocity_history) == 0:
            return current_pos

        velocity = self.velocity_history[-1]
        acceleration = self.get_acceleration()

        return current_pos + (velocity * prediction_time) + (0.5 * acceleration * prediction_time * prediction_time)