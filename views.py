from flask import Blueprint, render_template, redirect, url_for, Response, request
# import numpy as np
# import subprocess
# import time
# import ffmpeg
# import sys
# import cv2
# import threading

views = Blueprint("views", __name__)

# frame = None
# stopCaptureThread = False
# captureThread = None
# startYield = False


@views.route('/', methods=['POST', 'GET'])
def mainPage():
    return render_template('Home.html')


@views.route('/Stream', methods=['POST', 'GET'])
def streamPage():
    return render_template('Stream.html')


# @views.route('/play')
# def play():
#     global captureThread, stopCaptureThread, startYield
#     stopCaptureThread = False
#     captureThread = threading.Thread(target=captureImage, args=())
#     captureThread.daemon=True
#     captureThread.start()
#
#     startYield = True
#     return redirect(url_for('views.streamPage'))

#
# @views.route('/stop')
# def stop():
#     global stopCaptureThread, startYield, frame
#     stopCaptureThread = True
#     startYield = False
#     frame = None
#     print("Capture Thread successfully closed")
#     return redirect(url_for('views.streamPage'))
#
#
# @views.route('/video_feed')
# def video_feed():
#     if startYield:
#         return Response(gen(),
#                         mimetype='multipart/x-mixed-replace; boundary=frame')
#     else:
#         return Response()
#
#
# def gen():
#     global frame
#     while startYield:
#         if frame is not None and len(frame.shape) == 3:
#             frame2 = cv2.imencode('.jpg', frame)[1]
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + bytearray(frame2) + b'\r\n')
#
#
# def captureImage():
#     print("Capturing Image")
#     probe = ffmpeg.probe('rtsp://192.168.0.5:8080/h264.sdp')
#     cap_info = next(x for x in probe['streams'] if x['codec_type'] == 'video')
#     width = cap_info['width']
#     height = cap_info['height']
#     process1 = subprocess.Popen(['ffmpeg', '-fflags', 'nobuffer', '-flags', 'low_delay',
#                                  '-rtsp_transport', 'tcp',
#                                  '-i', 'rtsp://192.168.0.5:8080/h264.sdp',
#                                  '-f', 'rawvideo',
#                                  '-pix_fmt', 'bgr24',
#                                  '-r', '20',
#                                  'pipe:'], stdout=subprocess.PIPE)
#
#     # cv2.namedWindow("ffmpeg", cv2.WINDOW_NORMAL)
#     while True:
#         start = time.time()
#         frame_size = width * height * 3
#         in_bytes = process1.stdout.read(frame_size)
#         print(time.time() - start)
#         if not in_bytes:
#             break
#         in_frame = np.frombuffer(in_bytes, np.uint8).reshape([height, width, 3])
#         global frame
#         frame = in_frame
#         # cv2.imshow("ffmpeg", in_frame)
#         if cv2.waitKey(1) == ord('q') or stopCaptureThread:
#             # cv2.destroyAllWindows()
#             process1.terminate()
#             break
#
#         process1.stdout.flush()
#
