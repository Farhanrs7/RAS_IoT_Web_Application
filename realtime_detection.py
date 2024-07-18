import cv2
import numpy as np
import tensorflow as tf
import time

# import openpyx

# Load the label map
with open('labelmap.txt', 'r') as f:
    labels = [line.strip() for line in f.readlines()]


class RealtimeDetection:
    def __init__(self):

        # Initialize the TFLite interpreter
        self.interpreter = tf.lite.Interpreter(model_path='detect.tflite')
        self.interpreter.allocate_tensors()

        # Get model details
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.height = self.input_details[0]['shape'][1]
        self.width = self.input_details[0]['shape'][2]
        self.floating_model = (self.input_details[0]['dtype'] == np.float32)

        # Get the input scale and zero point from the input tensor
        self.input_mean = 127.5
        self.input_std = 127.5

        # Check output layer name to determine if this model was created with TF2 or TF1,
        # because outputs are ordered differently for TF2 and TF1 models
        self.outname = self.output_details[0]['name']

        self.boxes_idx, self.classes_idx, self.scores_idx = 1, 3, 0  # For TF2 model

        # Initialize video stream
        # cap = cv2.VideoCapture("Feeding 5 CCTV.mp4")
        # self.cap = cv2.VideoCapture(0)

        # w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        # h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # fps = self.cap.get(cv2.CAP_PROP_FPS)

        # self.result = cv2.VideoWriter("output_video.avi", cv2.VideoWriter_fourcc(*'XVID'), fps, (w, h))

        # Initialize frame rate calculation
        self.frame_rate_calc = 1
        self.freq = cv2.getTickFrequency()

        self.fps = 15
        self.frame_width = 1280
        self.frame_height = 720

        # Window setup
        # self.window_x = int((2160 - 1600) / 2)
        # self.window_y = int((1440 - 1000) / 2)
        # cv2.namedWindow('Object detector', cv2.WINDOW_NORMAL)
        # cv2.resizeWindow('Object detector', 800, 500)
        # cv2.moveWindow('Object detector', self.window_x, window_y)

        # Initialize detection-related variables
        self.min_conf_threshold = 0.4
        self.total_feeding_detected = 0
        self.detections_in_last_10s = 0
        self.last_10s_start_frame = 0
        self.last_10s_count = 0
        self.last_10s_count_display = 0
        self.first_detection_occurred = False

        # Initialize a list to store the inference times
        self.inference_times = []
        self.preferredShape = (360, 640, 3)


    def process(self, frame):
        if frame.shape != self.preferredShape:
            frame = cv2.resize(frame, (self.preferredShape[1], self.preferredShape[0]))
            display_frame = frame
        # Start timer (for calculating frame rate)
        t1 = cv2.getTickCount()

        # Acquire frame and resize to expected shape [1xHxWx3]
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (self.width, self.height))
        input_data = np.expand_dims(frame_resized, axis=0)

        # Normalize pixel values if using a floating model (i.e., if model is non-quantized)
        if self.floating_model:
            input_data = (np.float32(input_data) - self.input_mean) / self.input_std

        # Start the timer for inference time measurement
        start_time = time.time()

        # Perform the actual detection by running the model with the image as input
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        # Calculate the inference time
        inference_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        self.inference_times.append(inference_time)

        # Retrieve detection results
        boxes = self.interpreter.get_tensor(self.output_details[self.boxes_idx]['index'])[
            0]  # Bounding box coordinates of detected objects
        classes = self.interpreter.get_tensor(self.output_details[self.classes_idx]['index'])[
            0]  # Class index of detected objects
        scores = self.interpreter.get_tensor(self.output_details[self.scores_idx]['index'])[
            0]  # Confidence of detected objects

        # Loop over all detections and draw detection box if confidence is above minimum threshold
        imH, imW, _ = frame.shape
        for i in range(len(scores)):
            if ((scores[i] > self.min_conf_threshold) and (scores[i] <= 1.0)):
                # Get bounding box coordinates and draw box
                ymin = int(max(1, (boxes[i][0] * imH)))
                xmin = int(max(1, (boxes[i][1] * imW)))
                ymax = int(min(imH, (boxes[i][2] * imH)))
                xmax = int(min(imW, (boxes[i][3] * imW)))

                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (10, 255, 0), 2)

                # Draw label
                object_name = labels[int(classes[i])]
                label = '%s: %d%%' % (object_name, int(scores[i] * 100))
                labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                label_ymin = max(ymin, labelSize[1] + 10)
                cv2.rectangle(frame, (xmin, label_ymin - labelSize[1] - 10),
                              (xmin + labelSize[0], label_ymin + baseLine - 10), (255, 255, 255), cv2.FILLED)
                cv2.putText(frame, label, (xmin, label_ymin - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

                # Increment total feeding detections
                self.total_feeding_detected += 1

                # Check if this is the first detection
                if not self.first_detection_occurred:
                    self.first_detection_occurred = True
                    # last_10s_start_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                    self.last_10s_start_frame = self.fps

                # Calculate current frame position
                # current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                current_frame = self.fps

                # Calculate detections in last 10 seconds based on frames
                if current_frame - self.last_10s_start_frame <= 10 * self.fps:
                    self.last_10s_count += 1
                    self.detections_in_last_10s += 1
                else:
                    self.last_10s_count_display = self.detections_in_last_10s
                    last_10s_count = 1
                    detections_in_last_10s = 1
                    last_10s_start_frame = current_frame

        # Draw total detections counter on the frame (right side in black)
        total_counter_text = f'Total Feeding Detected: {self.total_feeding_detected}'
        total_counter_size, _ = cv2.getTextSize(total_counter_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        total_counter_x = frame.shape[1] - total_counter_size[0] - 30
        cv2.putText(frame, total_counter_text, (total_counter_x, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2,
                    cv2.LINE_AA)

        # Draw detections in last 10s counter on the frame (right side in black)
        last_10s_counter_text = f'Detections (Last 10s): {self.last_10s_count_display}'
        last_10s_counter_size, _ = cv2.getTextSize(last_10s_counter_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        last_10s_counter_x = frame.shape[1] - last_10s_counter_size[0] - 30
        cv2.putText(frame, last_10s_counter_text, (last_10s_counter_x, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2,
                    cv2.LINE_AA)

        # Draw average inference time on the frame (bottom right in black)
        avg_inference_time_text = f'Avg Inference Time: {np.mean(self.inference_times):.2f} ms'
        cv2.putText(frame, avg_inference_time_text, (750, 700), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2,
                    cv2.LINE_AA)

        # Calculate framerate
        t2 = cv2.getTickCount()
        time1 = (t2 - t1) / self.freq
        frame_rate_calc = 1 / time1

        # Draw framerate in corner of frame
        cv2.putText(frame, 'FPS: {0:.2f}'.format(frame_rate_calc), (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0),
                    2,
                    cv2.LINE_AA)

        return frame
