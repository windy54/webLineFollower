# import the necessary packages
from picamera.array import PiYUVArray
from picamera import PiCamera
from threading import Thread
import cv2
import time

class PiVideoStream:
	def __init__(self, resolution=(320, 240), framerate=20, **kwargs):
		# initialize the camera
		self.camera = PiCamera()

		# set camera parameters
		self.camera.resolution = resolution
		self.camera.framerate = framerate

		#  set optional camera parameters (refer to PiCamera docs)
		for (arg, value) in kwargs.items():
			setattr(self.camera, arg, value)

		# initialize the stream
		self.rawCapture = PiYUVArray(self.camera, size=resolution)
		self.stream = self.camera.capture_continuous(self.rawCapture,
			format="yuv", use_video_port=True)
		

		# initialize the frame and the variable used to indicate
		# if the thread should be stopped
		self.frame = None
		self.stopped = False

	def start(self):
		# start the thread to read frames from the video stream
		t = Thread(target=self.update, args=())
		t.daemon = True
		t.start()
		return self

	def update(self):
		# keep looping infinitely until the thread is stopped
		for f in self.stream:
			# grab the frame from the stream and clear the stream in
			# preparation for the next frame
			self.frame = f.array
			self.rawCapture.truncate(0)

			# if the thread indicator variable is set, stop the thread
			# and resource camera resources
			if self.stopped:
				self.stream.close()
				self.rawCapture.close()
				self.camera.close()
				return

	def read(self):
		# return the frame most recently read
		return self.frame

	def stop(self):
		# indicate that the thread should be stopped
		self.stopped = True

def main(args):
	cam = PiVideoStream()
	cam.start()
	time.sleep(1) #let camera warm up
	letsGo = True
	while letsGo:
		frame  = cam.read()
		cv2.imshow("full", frame)
		key = cv2.waitKey(1) & 0xFF
		if key == ord("q"):
			letsGo = False
	return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
