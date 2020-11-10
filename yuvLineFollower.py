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

def findLine(videoImage):
        hEnd , wEnd =videoImage.shape # get image width and height, processing starts at (0,0)
        tstart = time.time()
        lineCentre = -wEnd
        edges = np.zeros(shape=(hEnd ,wEnd)) # so numpy flips the index so an image (320 by 240) is stored in an array (240 by 320)
        mod = np.zeros(shape=(hEnd ,wEnd))	

        minLevel = np.min(videoImage,1) # find min and max levels of each row
        maxLevel = np.max(videoImage,1)
        # now for each apply adaptive threshold
        row = 0
        lineFound = False
        #for row in range(hEnd):
        while row < hEnd and not lineFound:
            # calculate the range for this row
            diff = maxLevel[row] - minLevel[row]
            edgep = []  # create an empty list to store edges   
            for col in range(wEnd):
            # now normalise if diff is not zero
                if diff !=0:
                    pixel = int((videoImage[row,col] - minLevel[row])*255/diff)
                else:
                    pixel = 0
                if pixel < 128: # if we are looking for a white line on a black background, test should be  > 128?
                    mod[row,col] = 250 
                else :
                    mod[row,col] = 0
                if col > 0:
                        edge = abs(mod[row,col] - mod[row,col-1])
                        edges[row,col] = edge
                        if edge >0 : # if it is an edge store it in list
                                edgep.append([row,col])
                        if len(edgep) == 2: # if on this row two edges have been found assume we have the line
                                '''
                                lineWidth = edgep[1][1]- edgep[0][1]
                                # this would need calibrating but my masking tape is 160 pixels wide for 2cm width
                        
                                if lineWidth > 50: 
                                        lineCentre = edgep[0][1]  + lineWidth /2
                                        lineFound = True
                                        #if row + 4 < hEnd:
                                        #    edges[row:row+4, edgep[0][1]:edgep[1][1] ] = 250
                                        break
                                '''
                                return [ edgep[0][1], edgep[1][1] ]
		    
            row+=1
        tdif = time.time() - tstart # use to monitor cycle time

        return [0, 0]
        


@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html")

def processImage():
	# grab global references to the video stream, output frame, and
	# lock variables
	global vs, outputFrame, lock, lineError
	# loop over frames from the video stream
	h = 240
	w = 320
	hStart = 200
	hEnd = 240
	hw = hEnd - hStart
	wStart = 20
	wEnd = 300
	ww = wEnd - wStart
	edges = np.zeros(shape=(hw ,ww)) # so numpy flips the index so an image (320 by 240) is stored in an array (240 by 320)
	mod = np.zeros(shape=(hw ,ww))		
	while True:
                startTime = time.time()
                frame = vs.read()
                ##############
                yChan = frame[hStart:hEnd,wStart:wEnd,0].copy() # extract a small area of the Y channel
                [ leftEdge, rightEdge] = findLine(yChan)
                # leftEdge and rightEdge are relative to the small window so need to add wStart to each one
		# because this added to each and then averaged, just add once below
                lineCentre = wStart + ( leftEdge + rightEdge ) /2
                lineError  =  ( 2 * lineCentre / ww ) - 1# ww is window width, so normalise to between + and - 1
                # blank out bottom part of image and draw lines for debug
                #frame[hStart:hEnd,wStart:wEnd,0] = np.zeros(shape=(hw, ww))
                #frame[hStart:hEnd,wStart:wEnd,1] = np.zeros(shape=(hw, ww))
                #frame[hStart:hEnd,wStart:wEnd,2] = np.zeros(shape=(hw, ww))	# clear out background	
                #frame[hStart:hEnd,wStart:wStart+280,1] = edges[:,:]# draw where edges are detected at top of screen
                frame[hStart-20:hEnd-20,int(lineCentre), 1] =250# draw vertical line on line centre
                frame[110:hEnd, int(w/2), 1] = 250

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
	t = threading.Thread(target=processImage, args=())
	t.daemon = True
	t.start()	# start a thread that will perform motion detection

	# start the flask app
	app.run(host="0.0.0.0", port="8000", debug=False,
		threaded=True, use_reloader=False)

# release the video stream pointer
vs.stop()
