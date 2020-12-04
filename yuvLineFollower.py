# USAGE
# python webstreaming.py --ip 0.0.0.0 --port 8000

# import the necessary packages
#from pyimagesearch.motion_detection import SingleMotionDetector
# this was based on pyimagesearch tutotial, I have rempved lkots of code but 
# have not updated comments and changed function names !

import yuvvideostream as yuv
from flask import Response
from flask import Flask
from flask import render_template
import threading
import argparse
import datetime
import imutils
import time
import cv2
import numpy as np
import matplotlib.pyplot as plt

global vs, outputFrame, lock, lineError
# need to define app at bgining
# initialize a flask object
app = Flask(__name__)

# this finds a line in the centre of the image
# it assumes that the passed matrix is one row of one channel of the captured image

def findEdges(videoRow):
	wEnd = len(videoRow)
	
	modified = np.zeros(wEnd)
	startPixel = 0
	endPixel = 0
	nValidPixels = 0
	lineCentres=[]
	pixels4ValidLine = 10
	for row in range(wEnd):
		pixel = videoRow[row]
		if pixel < 75: # less than 128 means black line > 128 means white
			modified[row] = 250 # so set black to max level
			if nValidPixels ==0:
				nValidPixels = 1
				startPixel = row
			else:
				nValidPixels+=1 # copund how many valid pixels we have for line
		else:
			if nValidPixels < pixels4ValidLine: # not enough consecutive points for line
				nValidPixels = 0
				startPixel = 0
			else:
				# enough points
				endPixel = row
				lineCentres.append((startPixel+endPixel)/2)
				nValidPixels = 0
				startPixel = 0

	# what if start detected and goes across all of video
	if nValidPixels > pixels4ValidLine :
		lineCentres.append((startPixel+row)/2)
	
	return lineCentres


@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html")

def recentreWindow(lineCentre, oldOffset):
	offset = oldOffset
	if lineCentre < 40 and oldOffset > 10:
		offset -= 10
	elif lineCentre > 80 and oldOffset < 200:  # really needs a variable w - window2Process
		offset += +10
	return offset
	
def processImage(h=240,w=320,hStart=200,hEnd=240,width=200):
	# grab global references to the video stream, output frame, and
	# lock variables
	global vs, outputFrame, lock, lineError
	# loop over frames from the video stream
	# currently using masking tape which has a width of 100 pixels 40 pixels from bottom of the image
	
	# lets set width of image to be processed
	wCentre = int(w/2)
	rows2Process = [160,180,200,220]
	nrows2Process = len(rows2Process)
	window2Process = 120
	rStart = [int(wCentre - window2Process/2)] * nrows2Process 
	letsGo = True    
	crossHeight = 20
	threshold = 50
	while letsGo:
		startTime = time.time()
		frame = vs.read()
		leftTurn = 0 # variables to indicate what has been detected
		centre = 0
		rightTurn = 0
		nCentres = 0
		
		##############
		for index in range(nrows2Process):
			row = rows2Process[index]
			
			rEnd = rStart[index] + window2Process
			
			processRow = frame[row,rStart[index] : rEnd ,0].copy()
			lineCentres = findEdges(processRow)
			
			#print(lineCentres)
			
			nFoundLines = len(lineCentres)
			if nFoundLines == 1: # only one valid centre so assume line
				nCentres+=1
				adj = int(lineCentres[0] + rStart[index])
				centre += adj # because rstart is now adaptable need to adjust each centre
				frame[row-crossHeight:row+crossHeight, adj, 1] = 250 # vertical line on centre
				rStart[index] = recentreWindow(lineCentres[0], rStart[index])
			elif nFoundLines > 1:
				# now need to discard lines
				for lc in lineCentres:
					adjust = int(lc + rStart[index])
					#print(int(wCentre-threshold))
					frame[row-crossHeight:row+crossHeight, adjust, 1] = 250 # vertical line on centre
					if abs (adjust - wCentre) < threshold:
						centre +=adjust
						nCentres+=1
						rStart[index] = recentreWindow(lc, rStart[index])
						
			frame[row,rStart[index] : rEnd,1] = 250 # draw line to show area that has been processed this will be next
			
		if nCentres >0:
			lineCentre = (centre / nCentres)
			lineError = 2 * lineCentre / width - 1
			#frame [:, int(lineCentre), 0 ] = 250 #this line seems to screw everything up!
			#print(rStart, centre, nCentres, width, lineError)
		else:
			lineError = -10
			
		frame [:, wCentre, 1 ] = 250
		#time.sleep(10)
		#print (lineCentre, lineError, 1.0 / (time.time()-startTime))
		


		##############
		# acquire the lock, set the output frame, and release the
		# lock
		
		with lock:
                        outputFrame = frame.copy()	
		
		loopTime = int( ( time.time()- startTime) * 1000)
		#print(loopTime)	
        

		
def generate():
	# grab global references to the output frame and lock variables
	global outputFrame, lock

	# loop over frames from the output stream
	while True:
		# wait until the lock is acquired
		with lock:
			#check if the output frame is available, otherwise skip
			# the iteration of the loop
			if outputFrame is None:
				continue

			# encode the frame in JPEG format
			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

			# ensure the frame was successfully encoded
			if not flag:
				continue

		# yield the output frame in the byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
			bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")	# start a thread that will perform motion detection

def video_feed():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate(),
		mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route('/lineError', methods=['GET'])
def getLineError():
	return str(lineError)
	

# check to see if this is the main thread of execution
if __name__ == '__main__':
	import json
	
	# load parameters if json file exists
	try:
		conf = json.load(open("yuvconf.json"))
		# camera resolution
		height = conf["height"]
		width = conf["width"]
		# row to start and end processing
		hStart = conf["hStart"]
		hEnd = conf["hEnd"]
		# width relative to centre of frame to process
		mainWindow = conf["mainWindow"]
		print("json file loaded")
	except Exception as e:
		print(e)
		height = 240
		width = 320
		hStart = 200
		hEnd = 240
		mainWindow = 200
		print("default parameters")
		
	# initialize the output frame and a lock used to ensure thread-safe
	# exchanges of the output frames (useful for multiple browsers/tabs
	# are viewing tthe stream)
	outputFrame = None
	lock = threading.Lock()
	
	# initialize the video stream and allow the camera sensor to
	# warmup
	kwargs={'hflip':True,'vflip':True}
	# default resolution is (320 wide by 240 high )
	vs = yuv.PiVideoStream(**kwargs).start()
	time.sleep(2.0)
	
	debug = False
	lineError = 0

	# start a thread that will perform motion detection
	t = threading.Thread(target=processImage, args=(height, width, hStart, hEnd, mainWindow))
	t.daemon = True
	t.start()	# start a thread that will perform motion detection

	# start the flask app
	app.run(host="0.0.0.0", port="8000", debug=False,
		threaded=True, use_reloader=False)

# release the video stream pointer
vs.stop()
