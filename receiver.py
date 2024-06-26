import asyncio
import os
import threading

import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration, MediaStreamTrack
from google.cloud import firestore
import logging
logger = logging.getLogger("pc")
logging.basicConfig(level=logging.INFO)
os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = "ras-iot-streaming-firebase-adminsdk-l9qma-8581f38285.json"

db = firestore.Client()

ICE_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun.l.google.com:5349"},
    {"urls": "stun:stun1.l.google.com:3478"},
    {"urls": "stun:stun1.l.google.com:5349"},
    {"urls": "stun:stun2.l.google.com:19302"},
    {"urls": "stun:stun2.l.google.com:5349"},
    {"urls": "stun:stun3.l.google.com:3478"},
    {"urls": "stun:stun3.l.google.com:5349"},
    {"urls": "stun:stun4.l.google.com:19302"},
    {"urls": "stun:stun4.l.google.com:5349"}
]
ice_servers = [RTCIceServer(x["urls"]) for x in ICE_SERVERS]

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
    try :
        while True:
            frame = await stream.recv()
            cv2.imshow('stream', frame)
            k = cv2.waitKey(1) & 0xFF
            if k == 27: #exit on escape
                cv2.destroyAllWindows()
                await pc.close()
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



pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(receiver())
loop.run_forever()
