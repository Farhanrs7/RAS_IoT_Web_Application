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
# p = subprocess.Popen(
#     ["C:/Users/farha/amazonkvswebrtc2/build/samples/kvsWebrtcClientViewerGstSample", "FishTankWebrtc", "video-only"],
#     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

ffmpeg_cmd = (
    ffmpeg.input("pipe:0", format='h264').video.output('pipe:1', format='rawvideo', pix_fmt='bgr24').compile()
)
ffmpegProcess = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)


class Receiver():
    def __init__(self, frame_width, frame_height):
        self.p = subprocess.Popen(
            ["C:/Users/farha/amazonkvswebrtc2/build/samples/kvsWebrtcClientViewerGstSample", "test", "video-only"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.FRAME_WIDTH = frame_width
        self.FRAME_HEIGHT = frame_height
        self.frame_queue = queue.Queue()
        self.stop_thread = False
        self.t1 = threading.Thread(target=self.sendFrameToFFMpeg, args=(self.p.stdout, ffmpegProcess.stdin,))
        self.t2 = threading.Thread(target=self.getFrameFromFFMpeg, args=(ffmpegProcess.stdout, self.frame_queue,))
        self.t1.daemon = True
        self.t2.daemon = True
        self.t1.start()
        self.t2.start()

    def stop(self):
        self.stop_thread = True
        self.t1.join()
        self.t2.join()
        print("both threads exited")
        self.p.terminate()
        print("kvs process terminated")

    def sendFrameToFFMpeg(self, out, ffmpegIn):
        while True:
            if self.stop_thread:
                break

            line = out.readline().strip()
            if line.find("Received frame:") != -1:
                frameBase64_ = line.split(":")[1]
                # print("thread1: " + frameBase64_)
                video_data = bytearray(base64.b64decode(frameBase64_))
                ffmpegIn.write(video_data)  # Write stream content to the pipe
                ffmpegIn.flush()

    def getFrameFromFFMpeg(self, ffmpegOut, frameq):
        while True:
            if self.stop_thread:
                print("exiting from thread")
                break
            # print("thread2: waiting for frame bytes")
            frame_bytes_ = ffmpegOut.read(self.FRAME_HEIGHT * self.FRAME_WIDTH * 3)
            ffmpegOut.flush()
            if frame_bytes_ is not None:
                # print("thread2: got frame_bytes")
                frame_ = numpy.frombuffer(frame_bytes_, numpy.uint8).reshape([self.FRAME_HEIGHT, self.FRAME_WIDTH, 3])
                frameq.put(frame_)
                size = frameq.qsize()
                if size > 100:
                    with frameq.mutex:
                        frameq.queue.clear()
                    print("thread2: cleared queue as length exceeds 100")
                print("thread2: added to queue, " + str(size))
