# USAGE
# upgardenPath.py

# import the necessary packages
#from pyimagesearch.motion_detection import SingleMotionDetector
# this was based on pyimagesearch tutotial, I have rempved lkots of code but 
# have not updated comments and changed function names !
'''

default image is 240 high by 320 wide
a row is processed to find the centre
0...................100.................160................220................319
the centre ofthe image is pixel 120, initially only pixels from 100 to 220 are processed, i.e. a window
120 pixels wide centred on the image. This window slides along the image according to where the centre of the line
is. This should steer the robot around a curve.
    wCentre = int(w/2)
	rows2Process = [160,180,200,220]  rows that are processed to find the line centre
	nrows2Process = len(rows2Process)
	window2Process = 120 specifies the width of the window
	wStartPixel = int(wCentre - window2Process/2) specifies the start point
	rStart = [wStartPixel] * nrows2Process # create a list of nrow2Process elements - start point for each row
then on each cycle rstart gets adjsuted according to where the centre of the line is, rduced by 10 if it is in the first
third, increased by 10 in the last third.
function findEdges(videoRow) processes the row and returns a list of line centres
This function just processes a list, so the same algorithm can be used to prcess a vertical list to look for the turns.
Left turns are ignored until there is a junctio with three options, here we must take the left turn.
So the algorithm looks for vertical lines either side of the image centre and when it finds them turns left.
The error is set to -1 and the window to process is biased to the left. (not yet tested!)
Our robot does not have a compass so we cant turn through a number of degrees, have to bias window to look left

The website displays the image and processed data in a strange format because I am processing a YUV image as jpeg
also /LoopTime displays the minimum, average and maximum proessing times to determine the frame rate, with the robot running
 seems to be 10 msecs or 100Hz.
'''
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

global vs, outputFrame, lock, lineError, minLoop, maxLoop, sumTime, sumCount
minLoop = 10000
maxLoop = 0
sumTime = 0
sumCount = 0
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
	global vs, outputFrame, lock, lineError, minLoop, maxLoop, sumTime, sumCount
	# loop over frames from the video stream
	# currently using masking tape which has a width of 100 pixels 40 pixels from bottom of the image
	
	# lets set width of image to be processed
	wCentre = int(w/2)
	rows2Process = [160,180,200,220]
	nrows2Process = len(rows2Process)
	window2Process = 120
	wStartPixel = int(wCentre - window2Process/2)
	rStart = [wStartPixel] * nrows2Process # create a list of nrow2Process elements
	letsGo = True    
	crossHeight = 20
	threshold = 50
	branchLeft = 0
	leftTurn = 0 # variables to indicate what has been detected
	
	# variables for vertical line
	rightTurn = 0
	rowStart = 100
	rowEnd   = 145
	column = 60
	rightOffset = 150
	while letsGo:
		startTime = time.time()
		frame = vs.read()
		centre = 0
		nCentres = 0
		
		##############  process horizontal lines
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
			else:
				rStart[index] = wStartPixel # have not found any lines so set to centre of image
						
			frame[row,rStart[index] : rEnd,1] = 250 # draw line to show area that has been processed this will be next
		
		# now process column
			
		frame[rowStart:rowEnd, column, 1] = 250
		processCol = frame[rowStart:rowEnd, column,0].copy()
		leftLine = findEdges(processCol)
		frame[rowStart:rowEnd, column + rightOffset, 1] = 250
		processCol = frame[rowStart:rowEnd, column + rightOffset,0].copy()
		rightLine = findEdges(processCol)
		lineError = -10
		if  leftLine and  rightLine:
			# detected a vertical line either side of the line we are following
			print (leftLine, rightLine)
			frame[int(rowStart + leftLine[0]), int(column  - 5):int(column  + 5), 1] = 250
			frame[int(rowStart + rightLine[0]), int(column + rightOffset - 5):int(column + rightOffset + 5), 1] = 250
			# rset window to left edge
			rStart = [20] * nrows2Process 
			lineError = -0.9
		elif nCentres >0:
			lineCentre = (centre / nCentres)
			lineError = 2 * lineCentre / width - 1		
			
		frame [:, wCentre, 1 ] = 250

		##############
		# acquire the lock, set the output frame, and release the
		# lock
		
		with lock:
			outputFrame = frame.copy()	
		
		# calculate loop time, then max min and sum to calculate average
		loopTime = int( ( time.time()- startTime) * 1000)
		sumTime += loopTime
		sumCount+=1
		if minLoop > loopTime:
			minLoop = loopTime
		if maxLoop < loopTime:
			maxLoop = loopTime
	
        

		
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



@app.route('/LoopTime', methods=['GET'])
def getloopTime():
	return str(maxLoop) + " " + str(sumTime/sumCount) + " " + str(minLoop)
	

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
