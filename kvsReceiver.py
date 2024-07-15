import base64
import queue
import subprocess
import sys
import threading
import time
import ffmpeg
import cv2
import numpy

print("Initializing subprocess")
p = subprocess.Popen(
    ["C:/Users/farha/amazonkvswebrtc2/build/samples/kvsWebrtcClientViewerGstSample", "FishTankWebrtc", "video-only"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

ffmpeg_cmd = (
    ffmpeg.input("pipe:0", format='h264').video.output('pipe:1', format='rawvideo', pix_fmt='bgr24').compile()
)
ffmpegProcess = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)


def sendFrameToFFMpeg(out, ffmpegIn):
    while True:
        line = out.readline().strip()
        if line.find("Received frame:") != -1:
            frameBase64_ = line.split(":")[1]
            # print("thread1: " + frameBase64_)
            video_data = bytearray(base64.b64decode(frameBase64_))
            ffmpegIn.write(video_data)  # Write stream content to the pipe
            ffmpegIn.flush()


class Receiver():
    def __init__(self, frame_width, frame_height):
        self.FRAME_WIDTH = frame_width
        self.FRAME_HEIGHT = frame_height
        self.frame_queue = queue.Queue()
        t1 = threading.Thread(target=sendFrameToFFMpeg, args=(p.stdout, ffmpegProcess.stdin,))
        t2 = threading.Thread(target=self.getFrameFromFFMpeg, args=(ffmpegProcess.stdout, self.frame_queue,))
        t1.daemon = True
        t2.daemon = True
        t1.start()
        t2.start()

    def getFrameFromFFMpeg(self, ffmpegOut, frameq):
        while True:
            # print("thread2: waiting for frame bytes")
            frame_bytes_ = ffmpegOut.read(self.FRAME_HEIGHT * self.FRAME_WIDTH * 3)
            ffmpegOut.flush()
            if frame_bytes_ is not None:
                # print("thread2: got frame_bytes")
                frame_ = numpy.frombuffer(frame_bytes_, numpy.uint8).reshape([self.FRAME_HEIGHT, self.FRAME_WIDTH, 3])
                frameq.put(frame_)
                print("thread2: added to queue, " + str(frameq.qsize()))
