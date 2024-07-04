import asyncio
import threading
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
from aiortc.contrib.media import MediaPlayer
from google.cloud import firestore
import os

import logging

logger = logging.getLogger("pc")
logging.basicConfig(level=logging.INFO)
# Set the path to your service account key file
os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = "ras-iot-streaming-firebase-adminsdk-l9qma-8581f38285.json"

db = firestore.Client()
# Define the ICE servers configuration
ice_servers = [
    {
        "urls": "stun:stun.l.google:19302"
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
                    loop.create_task(handleOffer(offer))
    callback_done.set()


# Watch the document
doc_offer_watch = offerDoc.on_snapshot(on_snapshot)


async def handleOffer(offer):
    # pc = RTCPeerConnection(RTCConfiguration(rtc_ice_servers))
    pc = RTCPeerConnection(configuration=RTCConfiguration([RTCIceServer(urls='stun:stun.l.google:19302')]))

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is " + pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()

    print(offer)
    await pc.setRemoteDescription(offer)
    player = MediaPlayer('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4')
    # player = MediaPlayer('rtsp://192.168.43.1:8080/h264.sdp')

    pc.addTrack(player.video)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    answerDict = {'sdp': answer.sdp, 'type': answer.type}
    answerDoc.set(answerDict)

    print("connection established")


async def sender():
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sender())
    loop.run_forever()
