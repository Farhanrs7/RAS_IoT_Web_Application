import threading
import time

import cv2
from flask import Flask, Response

from kvsReceiver import Receiver


def create_app():
    app = Flask("fish tank http mjpeg stream")
    app.config['SECRET_KEY'] = 'secret'
    return app


app = create_app()
receiver = None


@app.route('/mjpeg')
def mjpeg():
    global receiver
    try:
        if receiver is None:
            receiver = Receiver(1280, 720, "test")
        response = Response(gen(),
                            mimetype='multipart/x-mixed-replace; boundary=frame')
        return response
    except Exception as e:
        print("got exception on response func")


def gen():
    global receiver
    try:
        while receiver is not None:
            frame = receiver.frame_queue.get()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(1)
    except GeneratorExit:
        print("Client disconnected.")
        if receiver is not None:
            print("Stopping receiver")
            receiver.stop()
            receiver = None


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, threaded=True)
