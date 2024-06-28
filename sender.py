import asyncio
import threading
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration
from aiortc.contrib.media import MediaPlayer
from google.cloud import firestore
import os

# import nest_asyncio
#
# nest_asyncio.apply()

# Set the path to your service account key file
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
offerDoc.delete()
answerDoc = db.collection("calls").document("answers")

# Create an Event for notifying main thread.
callback_done = threading.Event()


# Create a callback on_snapshot function to capture changes
def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        if doc.id == "offers":
            for change in changes:
                if change.type.name == "ADDED":
                    print("Offer Received")
                    offerDict = doc.to_dict()
                    offer = RTCSessionDescription(sdp=offerDict['sdp'], type=offerDict['type'])
                    task2 = loop.create_task(handleOffer(offer))
                    tasks.append(task2)
    callback_done.set()


# Watch the document
doc_offer_watch = offerDoc.on_snapshot(on_snapshot)


async def handleOffer(offer):
    if offer:
        print(offer)
        await pc.setRemoteDescription(offer)
        player = MediaPlayer('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4')
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
    # Create peer connection
    pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sender())
    loop.run_forever()
