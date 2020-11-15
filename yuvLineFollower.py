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
# it assumes that the passed matrix is one colour channel of the captured image

def findEdges(videoRow):
    wEnd = len(videoRow)
    minLevel = np.min(videoRow)
    maxLevel = np.max(videoRow)
    diffLevel = maxLevel-minLevel
    modified = np.zeros(wEnd)
    startPixel = 0
    endPixel = 0
    nValidPixels = 0
    lineCentres=[]
    for row in range(wEnd):
        if diffLevel !=0:
            pixel = int((videoRow[row] - minLevel)*255/diffLevel)
            if pixel < 128: # less than 128 means black line > 128 means white
                modified[row] = 250 # so set black to max level
                if nValidPixels ==0:
                    nValidPixels = 1
                    startPixel = row
                else:
                    nValidPixels+=1 # copund how many valid pixels we have for line
            else:
                if nValidPixels < 3: # not enough consecutive points for line
                    nValidPixels = 0
                    startPixel = 0
                else:
                    # enough points
                    endPixel = row
                    lineCentres.append((startPixel+endPixel)/2)
                    nValidPixels = 0
                    startPixel = 0

    # what if start detected and goes across all of video
    if nValidPixels > 3 :
        lineCentres.append((startPixel+row)/2)

    return lineCentres


@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html")

def processImage(h=240,w=320,hStart=200,hEnd=240,width=200):
	# grab global references to the video stream, output frame, and
	# lock variables
	global vs, outputFrame, lock, lineError
	# loop over frames from the video stream
	# currently using masking tape which has a width of 100 pixels 40 pixels from bottom of the image
	
	rows2Process = [120, 160, 200]
	hw = hEnd - hStart
	# lets set width of image to be processed
	wCentre = w/2
	wStart =  int((w - width ) /2)#20
	wEnd =  int((w + width ) /2)#300
	ww = wEnd - wStart
	edges = np.zeros(shape=(hw ,ww)) # so numpy flips the index so an image (320 by 240) is stored in an array (240 by 320)
	mod = np.zeros(shape=(hw ,ww))  
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
		for row in rows2Process:
			processRow = frame[row,wStart:wEnd,0].copy()
			lineCentres = findEdges(processRow)
			nFoundLines = len(lineCentres)
			if nFoundLines == 1: # only one valid centre so assume line
				centre += lineCentres[0]
				nCentres+=1
				adj = int(lineCentres[0] + wStart)
				frame[row-crossHeight:row+crossHeight, adj, 1] = 250
			elif nFoundLines > 1:
				# now need to discard lines
				for lc in lineCentres:
					adjust = int(lc + wStart)
					frame[row-crossHeight:row+crossHeight, adjust, 1] = 250
					if abs (adjust - wCentre) < threshold:
						centre +=lc
						nCentres+=1
		if nCentres >0:
			lineCentre =  wStart + (centre / nCentres)
			lineError = 2 * lineCentre / width - 1
		else:
			lineError = -10
			
		#print (lineCentre, lineError, 1.0 / (time.time()-startTime))
		frame[row,wStart:wEnd,1] = 250


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
