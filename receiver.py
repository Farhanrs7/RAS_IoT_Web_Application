import asyncio
import base64
import json
import os
import threading
import time

import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration, MediaStreamTrack
from google.cloud import firestore
import logging
logger = logging.getLogger("pc")
logging.basicConfig(level=logging.INFO)
os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = "ras-iot-streaming-firebase-adminsdk-l9qma-8581f38285.json"


db = firestore.Client()

# Define the ICE servers configuration
ice_servers = [
    {
        "urls": "stun:stun.relay.metered.ca:80"
    },
    {
        "urls": "stun:stun.l.google:19302"
    },
    {
        "urls": "turn:global.relay.metered.ca:80",
        "username": "1d20821c81d036448471a287",
        "credential": "2yTtqTWHgkN8Jog4",
    },
    {
        "urls": "turn:global.relay.metered.ca:80?transport=tcp",
        "username": "1d20821c81d036448471a287",
        "credential": "2yTtqTWHgkN8Jog4",
    },
    {
        "urls": "turn:global.relay.metered.ca:443",
        "username": "1d20821c81d036448471a287",
        "credential": "2yTtqTWHgkN8Jog4",
    },
    {
        "urls": "turns:global.relay.metered.ca:443?transport=tcp",
        "username": "1d20821c81d036448471a287",
        "credential": "2yTtqTWHgkN8Jog4",
    },
]
# Define the ICE servers configuration
ice_servers2 = [
    {
        "urls": "turn:openrelay.metered.ca:80",
        "username": "openrelayproject",
        "credential": "openrelayproject",
    }
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


offerDoc = db.collection("calls").document("offers")
answerDoc = db.collection("calls").document("answers")
# answerDoc.delete()
# offerDoc.delete()

# Create an Event for notifying main thread.
callback_done = threading.Event()


# Create a callback on_snapshot function to capture changes
def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        if doc.id == "answers":
            for change in changes:
                if change.type.name == "ADDED":
                    print("Answer Received")
                    answerDict = doc.to_dict()
                    answer = RTCSessionDescription(sdp=answerDict['sdp'], type=answerDict['type'])
                    loop.create_task(handleAnswer(answer))
    callback_done.set()


# Watch the document
doc_answer_watch = answerDoc.on_snapshot(on_snapshot)


async def handleAnswer(answer):
    await pc.setRemoteDescription(answer)


class VideoFrameReceiver(MediaStreamTrack):
    def __init__(self):
        super().__init__()
        self.track = None

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")
        # Process frame (img) here
        return img


async def displayFrames(stream):
    try:
        while True:
            frame = await stream.recv()
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(bytes(buffer)).decode('utf-8')
            print(frame_base64)
    except:
        print("Stopping display frames")


async def receiver():
    pc.addTransceiver("video", direction="recvonly")
    video_stream = VideoFrameReceiver()

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is " + pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()

    @pc.on("track")
    def on_track(track):
        print("Track Received")
        if track.kind == "video":
            print(track.kind)
            video_stream.track = track
            loop.create_task(displayFrames(video_stream))

    # Create offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    offer = {'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}
    offerDoc.set(offer)
    print("Offer Sent")
    while True:
        await asyncio.sleep(1)


# pc = RTCPeerConnection(configuration=RTCConfiguration(rtc_ice_servers))
pc = RTCPeerConnection(configuration=RTCConfiguration([RTCIceServer(urls='stun:stun.l.google:19302')]))

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(receiver())
loop.run_forever()
