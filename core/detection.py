# original

import numpy as np
import collections


def find_line_position(gray_array, sensitivity_threshold=50, min_height_ratio=0.7):
    height, width = gray_array.shape
    if width < 3:
        return -1
    left_cols = gray_array[:, :-2].astype(np.float32)
    center_cols = gray_array[:, 1:-1].astype(np.float32)
    right_cols = gray_array[:, 2:].astype(np.float32)
    gradients = np.abs(center_cols - left_cols) + np.abs(center_cols - right_cols)
    vertical_sum = np.sum(gradients, axis=0)
    best_x = -1
    max_gradient_sum = -1
    thresh = sensitivity_threshold * height * 0.2
    candidate_indices = np.where(vertical_sum > thresh)[0]
    strong_edge_threshold = sensitivity_threshold * 0.5
    min_pixels = height * min_height_ratio
    for x_idx in candidate_indices:
        x = x_idx + 1
        col_gradients = gradients[:, x_idx]
        if np.sum(col_gradients > strong_edge_threshold) >= min_pixels:
            current_sum = vertical_sum[x_idx]
            if current_sum > max_gradient_sum:
                max_gradient_sum = current_sum
                best_x = x
    return best_x


class VelocityCalculator:
    def __init__(self, history_length=10):
        self.position_history = collections.deque(maxlen=history_length)
        self.velocity_history = collections.deque(maxlen=5)

    def add_position(self, position, timestamp):
        if position == -1:
            return 0
        self.position_history.append((position, timestamp))
        return self.calculate_velocity()

    def calculate_velocity(self):
        if len(self.position_history) < 2:
            return 0

        valid_points = [(pos, t) for pos, t in self.position_history if pos != -1]
        if len(valid_points) < 2:
            return 0

        if len(valid_points) >= 3:
            velocity = self._weighted_velocity(valid_points)
        else:
            pos1, t1 = valid_points[-2]
            pos2, t2 = valid_points[-1]
            dt = t2 - t1
            velocity = (pos2 - pos1) / dt if dt > 0 else 0

        self.velocity_history.append(velocity)
        return self._smooth_velocity()

    def _weighted_velocity(self, points):
        if len(points) < 3:
            return 0

        weights = np.exp(np.linspace(-1, 0, len(points)))
        weights = weights / np.sum(weights)

        velocities = []
        for i in range(1, len(points)):
            pos1, t1 = points[i - 1]
            pos2, t2 = points[i]
            dt = t2 - t1
            if dt > 0:
                velocities.append((pos2 - pos1) / dt)

        if not velocities:
            return 0

        if len(velocities) == 1:
            return velocities[0]

        velocity_weights = weights[-len(velocities):]
        velocity_weights = velocity_weights / np.sum(velocity_weights)

        return np.average(velocities, weights=velocity_weights)

    def _smooth_velocity(self):
        if len(self.velocity_history) == 0:
            return 0
        if len(self.velocity_history) == 1:
            return self.velocity_history[-1]

        weights = np.array([0.1, 0.2, 0.3, 0.4, 0.5])[-len(self.velocity_history):]
        weights = weights / np.sum(weights)

        return np.average(list(self.velocity_history), weights=weights)

    def get_acceleration(self):
        if len(self.velocity_history) < 2:
            return 0

        recent_velocities = list(self.velocity_history)[-3:]
        if len(recent_velocities) < 2:
            return 0

        time_interval = 1.0 / 120.0
        accel = (recent_velocities[-1] - recent_velocities[0]) / (time_interval * (len(recent_velocities) - 1))
        return accel

    def predict_position(self, current_pos, target_pos, current_time, prediction_time):
        if len(self.velocity_history) == 0:
            return current_pos

        velocity = self.velocity_history[-1]
        acceleration = self.get_acceleration()

        predicted_pos = current_pos + (velocity * prediction_time) + (
                0.5 * acceleration * prediction_time * prediction_time)

        return predicted_pos