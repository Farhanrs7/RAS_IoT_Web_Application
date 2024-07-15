import base64
import queue
import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors
from collections import defaultdict
import math
import time


class AiModel():
    def __init__(self):
        # Initialize tracking history and model
        self.track_history = defaultdict(list)
        self.model = YOLO("best.pt")
        self.names = self.model.model.names

        # Variables for fish counting and time tracking
        self.fish_speeds = defaultdict(list)
        self.predict = "feed"
        self.start_time = time.time()
        self.counting_period = 10  # seconds for test feeding
        self.real_feeding_period = 10  # seconds for real feeding
        self.Stop_count = 0  # Initialize Stop_count

        # Variables for frame rate adjustment
        self.prev_time = time.time()

        self.seen_track_ids = set()

        # Accumulated results
        self.decision_history = []
        self.count_history = []
        self.speed_history = []

        self.preferredShape = (360, 640, 3)

    def aiTask(self, frame):
        if frame is not None:
            # Create a copy of the frame for real-time display
            display_frame = frame
            print(frame.shape)

            if frame.shape != self.preferredShape:
                frame = cv2.resize(frame, (self.preferredShape[1], self.preferredShape[0]))
                display_frame = frame
            results = self.model.track(frame, persist=True, verbose=False)
            boxes = results[0].boxes.xyxy.cpu()
            frame_fish_count = 0
            avg_speed = "N/A"  # Initialize avg_speed as "N/A"

            if results[0].boxes.id is not None:
                # Extract prediction results
                clss = results[0].boxes.cls.cpu().tolist()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                confs = results[0].boxes.conf.float().cpu().tolist()

                # Annotator Init with larger line width
                annotator = Annotator(display_frame, line_width=2)  # Increase the line width here

                unique_fish_in_frame = set(track_ids)  # Unique fish in the current frame
                frame_fish_count = len(unique_fish_in_frame)
                self.seen_track_ids.update(unique_fish_in_frame)  # Update the set of seen track IDs

                for box, cls, track_id in zip(boxes, clss, track_ids):
                    # Draw the bounding box
                    annotator.box_label(box, color=colors(int(cls), True), label="")

                    # Create label with class name and tracking ID
                    label = f"{self.names[int(cls)]} {track_id}"
                    (label_width, label_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 1, 1)
                    label_ymin = max(int(box[1]) - label_height - 10, 0)
                    label_rect = [(int(box[0]), label_ymin), (int(box[0]) + label_width, int(box[1]))]

                    # Draw label background
                    cv2.rectangle(display_frame, label_rect[0], label_rect[1], colors(int(cls), True), -1)

                    # Draw label text
                    cv2.putText(display_frame, label, (int(box[0]), label_ymin + label_height + baseline - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

                    # Store tracking history
                    track = self.track_history[track_id]
                    current_position = (int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2))
                    track.append(current_position)
                    if len(track) > 30:
                        track.pop(0)

                    distance = 0
                    # Calculate speed (pixels per second)
                    if len(track) > 1:
                        dx = track[-1][0] - track[-2][0]
                        dy = track[-1][1] - track[-2][1]
                        distance = math.sqrt(dx ** 2 + dy ** 2)
                    speed = (distance * 20)  # pixels per second

                    # Draw speed on the frame
                    speed_label = f"Speed: {speed:.2f} px/s"
                    cv2.putText(display_frame, speed_label, (int(box[0]), label_ymin - 20), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                (0, 255, 0), 1)

                    # Record speed for averaging
                    self.fish_speeds[track_id].append(speed)
                    if len(self.fish_speeds[track_id]) > 30:
                        self.fish_speeds[track_id].pop(0)

                    # Plot tracks
                    points = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
                    cv2.circle(display_frame, track[-1], 7, colors(int(cls), True), -1)
                    cv2.polylines(display_frame, [points], isClosed=False, color=colors(int(cls), True),
                                  thickness=2)  # Increase thickness here

                if self.fish_speeds:
                    avg_speed = sum(map(np.mean, self.fish_speeds.values())) / len(self.fish_speeds)
                    avg_speed = f"{avg_speed:.2f} px/s"

            bottom_margin = 40
            line_spacing = 40
            h = display_frame.shape[0]

            cv2.putText(display_frame, f"Fish per frame: {frame_fish_count}", (10, h - bottom_margin),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(display_frame, f"Accumulated fish: {len(self.seen_track_ids)}",
                        (10, h - bottom_margin - line_spacing),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(display_frame, f"Average Speed: {avg_speed}", (10, h - bottom_margin - 2 * line_spacing),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            fps = 20
            curr_time = time.time()
            processing_time = curr_time - self.prev_time

            # sleep_duration = max(0, (1 / fps) - processing_time)
            # time.sleep(sleep_duration)
            prev_time = curr_time

            # result.write(display_frame)
            elapsed_time = time.time() - self.start_time
            if elapsed_time >= self.counting_period:
                avg_speed_value = float(avg_speed.split()[0]) if avg_speed != "N/A" else 0
                if len(self.seen_track_ids) > 8 and avg_speed_value > 300:
                    real_feeding = "High"
                    Stop_count = 0
                    counting_period = 5
                    self.decision_history.append("High\n")
                    self.count_history.append(str(len(self.seen_track_ids)) + '\n')
                    self.speed_history.append(str(avg_speed_value) + '\n')
                elif len(self.seen_track_ids) > 8 or avg_speed_value > 300:
                    real_feeding = "Low"
                    Stop_count = 0
                    counting_period = 5
                    self.decision_history.append("Low\n")
                    self.count_history.append(str(len(self.seen_track_ids)) + '\n')
                    self.speed_history.append(str(avg_speed_value) + '\n')
                elif len(self.seen_track_ids) < 8 and avg_speed_value < 300:
                    real_feeding = "stop"
                    self.Stop_count += 1
                    self.count_history.append(str(len(self.seen_track_ids)) + '\n')
                    self.speed_history.append(str(avg_speed_value) + '\n')

                    if self.Stop_count == 1:
                        self.decision_history.append("First stop feeding decision\n")
                        counting_period = 10
                    elif self.Stop_count == 2:
                        self.decision_history.append("Second stop feeding decision. STOP!\n")
                        # break  # uncomment this line to stop the detection
                    else:
                        self.decision_history.append("Should stop feeding decision\n")
                        # break  # uncomment this line to stop the detection

                seen_track_ids = set()  # Reset accumulated fish count
                start_time = time.time()

            # Update Streamlit components
            # decision_results.markdown('\n'.join(decision_history))
            # count_results.markdown('\n'.join(count_history))
            # speed_results.markdown('\n'.join(speed_history))

            return display_frame

# cap = cv2.VideoCapture(1)  # Open the default camera
#
# if __name__ == "__main__":
#     print("running")
#     model = AiModel()
#     while True:
#         print(cap.isOpened())
#         # Capture the video frame
#         # by frame
#         ret, frame = cap.read()
#         # print(frame)
#         if frame is not None:
#             display_frame = model.aiTask(frame)
#
#             cv2.imshow('ai', display_frame)
#             if cv2.waitKey(1) & 0xFF == ord("q"):
#                 cv2.destroyAllWindows()
#                 break
