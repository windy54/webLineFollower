# USAGE
# singleRow.py
# processes a frame at a time and displays intermediate output
# to enable algorithm development
# import the necessary packages
#from pyimagesearch.motion_detection import SingleMotionDetector
# this was based on pyimagesearch tutotial, I have removed loots of code but 
# have not necessarily updated comments and changed function names !

import yuvvideostream as yuv

import datetime
import imutils
import time
import cv2
import numpy as np
import matplotlib.pyplot as plt

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
    #print(modified)
    #print(lineCentres)
    return lineCentres

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
                    pixel = int((videoImage[row,col] - minLevel[row])*255/diff) # normalise pixel
                else:
                    pixel = 0
                if pixel < 128: # if we are looking for a white line on a black background, test should be  > 128?
                    mod[row,col] = 250 
                else :
                    mod[row,col] = 0
                if col > 0:
                        edge = abs(mod[row,col] - mod[row,col-1])
                        edges[row,col] = edge
                        #print(row,col,edge)
                        if edge >0 : # if it is an edge store it in list
                                edgep.append([row,col])
                        #if len(edgep) == 2: # if on this row two edges have been found assume we have the line
                        #        return [ edgep[0][1], edgep[1][1], edges, mod ]
            # if we get here then no edge has been found, but maybe the start has been found
            if len(edgep) ==1:
                # we have a start
                print("start found at ", row,col,mod[row,col],edgep)
                #return [ edgep[0][1], col, edges, mod]
            
            row+=1
        tdif = time.time() - tstart # use to monitor cycle time

        return [0, 0, edges, mod]
        




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
            print(centre, nCentres)
        lineCentre =  wStart + (centre / nCentres)
        lineError = 2 * lineCentre / threshold - 1
        print (lineCentre, lineError, 1.0 / (time.time()-startTime))
        frame[row,wStart:wEnd,1] = 250
        
        cv2.imshow('image',frame)
        #cv2.imshow('edges',edges)
        #cv2.imshow('normalised',mod)
        k = cv2.waitKey(1) & 0xFF
        if k == 27: # escape
            break
        
        time.sleep(2)
        carryOn = input("press any key to carry on, Q to quit")
        if carryOn == "q":
            letsGo = False
        


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
        

    
    # initialize the video stream and allow the camera sensor to
    # warmup
    kwargs={'hflip':True,'vflip':True}
    # default resolution is (320 wide by 240 high )
    vs = yuv.PiVideoStream(**kwargs).start()
    time.sleep(2.0)
    processImage(height,width,hStart,hEnd,mainWindow)
 


# release the video stream pointer
vs.stop()
