import threading
import time
import queue
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, RTCIceServer, RTCConfiguration
from aiortc.contrib.media import MediaRelay
from flask import Flask
from google.cloud import firestore
from views import views
import asyncio
import logging
import os
from frameAi import AiModel

from av import VideoFrame

logger = logging.getLogger("__main__")
logging.basicConfig(level=logging.INFO)

# Set the path to your service account key file
os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = "ras-iot-streaming-firebase-adminsdk-l9qma-8581f38285.json"

db = firestore.Client()

relay = MediaRelay()

offerDoc = db.collection("calls").document("offers")
offerDoc.delete()
answerDoc = db.collection("calls").document("answers")
answerDoc.delete()
# Create an Event for notifying main thread.
callback_done = threading.Event()


# Create a callback on_snapshot function to capture changes
def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        if doc.id == "offers":
            print("offers")
            for change in changes:
                if change.type.name == "ADDED":
                    print("Offer Received")
                    offerDict = doc.to_dict()
                    offer = RTCSessionDescription(sdp=offerDict['sdp'], type=offerDict['type'])
                    loop.run_until_complete(receiver(offer))
    callback_done.set()


# Watch the document
doc_offer_watch = offerDoc.on_snapshot(on_snapshot)

ice_servers = [
    {
        "urls": "stun:stun.relay.metered.ca:80"
    },
    {
        "urls": "turn:sg.relay.metered.ca:80",
        "username": "1d20821c81d036448471a287",
        "credential": "2yTtqTWHgkN8Jog4",
    },
    {
        "urls": "turn:sg.relay.metered.ca:80?transport=tcp",
        "username": "1d20821c81d036448471a287",
        "credential": "2yTtqTWHgkN8Jog4",
    },
    {
        "urls": "turn:sg.relay.metered.ca:443",
        "username": "1d20821c81d036448471a287",
        "credential": "2yTtqTWHgkN8Jog4",
    },
    {
        "urls": "turns:sg.relay.metered.ca:443?transport=tcp",
        "username": "1d20821c81d036448471a287",
        "credential": "2yTtqTWHgkN8Jog4",
    },
]
# Convert the dictionary to RTCIceServer objects
rtc_ice_servers = []
for server in ice_servers:
    rtc_ice_server = RTCIceServer(
        urls=server["urls"],
        username=server.get("username"),
        credential=server.get("credential"),
    )
    rtc_ice_servers.append(rtc_ice_server)


class VideoFrameReceiver(MediaStreamTrack):
    kind = "video"

    def __init__(self, track):
        super().__init__()
        self.track = track
        self.model = AiModel()
        self.frame = None
        self.firstFrame = None
        self.frameArr = []
        self.frameQueue = asyncio.LifoQueue(maxsize=1)

    async def recv(self):
        while True:
            start = time.time()
            frame = await self.track.recv()
            diff = time.time() - start
            print(diff)
            if diff > 0.1:
                break
        # time.sleep(0.5)
        # start = time.time()
        # frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")
        # diff = time.time() - start
        # print(diff)
        # print(img.shape)
        resultImg = self.model.aiTask(img)
        # # cv2.imshow('ai',resultImg)
        # # cv2.waitKey(1)
        new_frame = VideoFrame.from_ndarray(resultImg, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base
        return new_frame
        # return frame


async def receiver(offer):
    print("Initializing receiver")
    # pc = RTCPeerConnection(RTCConfiguration(iceServers=[RTCIceServer(urls='stun:stun.l.google.com:19302')]))
    pc = RTCPeerConnection(RTCConfiguration(iceServers=None))

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is " + pc.connectionState)
        if pc.connectionState == "failed":
            cv2.destroyAllWindows()
            await pc.close()

    @pc.on("track")
    def on_track(track):
        print(track.kind)
        if track.kind == 'video':
            videoFrame = VideoFrameReceiver(relay.subscribe(track))
            pc.addTrack(videoFrame)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    answerDict = {'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}
    answerDoc.set(answerDict)
    while True:
        await asyncio.sleep(1)
        if pc.connectionState == "closed":
            break
    print("exiting")


async def displayFrames(stream):
    print("waiting for video frames")
    cv2.namedWindow("stream", cv2.WINDOW_NORMAL)  # Create window with freedom of dimensions
    while True:
        try:
            frame = await stream.recv()
            img = frame.to_ndarray(format="bgr24")
            print(img.shape)
            cv2.imshow('stream', img)
            cv2.waitKey(1)
        except Exception as e:
            print("error :", e)
            cv2.destroyAllWindows()


def create_app():
    app = Flask("Fish Tank camera webserver")
    app.config['SECRET_KEY'] = 'secret'
    app.register_blueprint(views)
    return app


application = create_app()
# CORS(application,resources={r"/*":{"origins":"*"}})
# socketio = SocketIO(application,cors_allowed_origins="*")


# @socketio.on("frameFromBrowser")
# def resendFrame(data):
#     print(data)
#     time.sleep(1)
#     emit('frameFromServer', "hello,im frame")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application.run(host='0.0.0.0', port=8000, threaded=True)
