import time

import cv2
from flask import Blueprint, render_template, redirect, url_for, Response, request, jsonify

import kvsReceiver
from kvsReceiver import Receiver
# import numpy as np
# import subprocess
# import time
# import ffmpeg
# import sys
# import cv2
import threading
import os
from google.cloud import firestore
from datetime import datetime
#from frameAi import AiModel

# from realtime_detection import RealtimeDetection
views = Blueprint("views", __name__)

# Set the path to your service account key file
os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = "ras-iot-streaming-firebase-adminsdk-l9qma-8581f38285.json"

db = firestore.Client()

feedDoc = db.collection("feeding").document("signals")


# frame = None
# stopCaptureThread = False
# captureThread = None
# startYield = False
receiver = None


# model = AiModel()
# model = RealtimeDetection()

# receiver = Receiver(1280, 720)


# cam = cv2.VideoCapture(0)

@views.route('/', methods=['POST', 'GET'])
def mainPage():
    return render_template('Home.html')


@views.route('/Stream', methods=['POST', 'GET'])
def streamPage():
    return render_template('Stream.html')


@views.route('/startStreaming', methods=['POST','GET'])
def startStreaming():
    channel_name = request.json.get('param')
    print("stream button clicked")
    global receiver
    if receiver is None:
        receiver = Receiver(1280, 720,channel_name)
    return {'success': True}


@views.route('/stopStreaming')
def stopStreaming():
    print("stop button clicked")
    global receiver
    if receiver is not None:
        print("Stopping receiver")
        receiver.stop()
        receiver = None
    return {'success': True}


@views.route('/feed', methods=['POST', 'GET'])
def feed():
    text = request.json.get('text')
    # datetime object containing current date and time
    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    feedDoc.set({"feed amount" : text, "feed time": dt_string})
    return jsonify({"message": "Sending signal to RPI...."})


@views.route('/video_feed')
def video_feed():
    print("doing vidoe feed")
    response = Response(gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    return response


def gen():
    while True:
        if receiver is not None:
            # print("waiting for queue")
            frame = receiver.frame_queue.get()

            # success, frame = cam.read()
            # time.sleep(2)
            # cv2.imshow('stream', frame)
            # if cv2.waitKey(1) & 0xFF == 27:
            #     cv2.destroyAllWindows()
            # break
            # frame = model.process(frame)
            # frame = model.aiTask(frame)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.01)
