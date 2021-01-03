# Need floating point division of integers
from __future__ import division

import time
from time import sleep

import os
import requests

try:
    import redboard
    print("redboard")


    class redBoardRobot():
    
        def set_speeds(power_left, power_right,motor_multiplier=1.0):
            """
            As we have an motor hat, we can use the motors
            :param power_left: 
                Power to send to left motor
            :param power_right: 
                Power to send to right motor, will be inverted to reflect chassis layout
            """
            
            # If one wants to see the 'raw' 0-100 values coming in
            #print("source left: {}".format(power_left))
            #print("source right: {}".format(power_right))
            
            
            # Take the 0-100 inputs down to 0-1 and reverse them if necessary
            # this comment relates to the gpio zero robot and camjam board
            # we are using redboard motor controller and that wants demand +/-100
            power_left = (motor_multiplier * power_left) 
            power_right = (motor_multiplier * power_right) 
            
            # Print the converted values out for debug
            #print("left: {}".format(power_left))
            #print("right: {}".format(power_right))
            
            # If power is less than 0, we want to turn the motor backwards, otherwise turn it forwards
            # m1 is connected to left motor, +ve sends it forward
            redboard.M1(power_left)
            # m2 is connected to right motor, +ve sneds it backwards, hence we invert
            
            redboard.M2(-power_right)
            
            
        def stop_motors():
            """
            As we have an motor hat, stop the motors using their motors call
            """
            # Turn both motors off
            redboard.Stop()
    robot = redBoardRobot()

except:
    
    # Use GPIO Zero implementation of CamJam EduKit robot (thanks Ben Nuttall/Dave Jones!)
    from gpiozero import Motor, LED
 
    class MecRobot():
    
        def __init__(self):
            self.frontLeft = Motor(6, 13)
            self.frontRight = Motor(9, 11)
            self.rearLeft = Motor(20, 21)
            self.rearRight = Motor(17, 27)
            # Motors are reversed. If you find your robot going backwards, set this to 1
            self.motor_multiplier = -1
            self.red = LED(16)
            self.red.blink()
            self.LineFollowingError = -1
    
    
        def set_speeds(self,power_left, power_right):
           
        
            # If one wants to see the 'raw' 0-100 values coming in
            # print("source left: {}".format(power_left))
            # print("source right: {}".format(power_right))
        
            # Take the 0-100 inputs down to 0-1 and reverse them if necessary
            power_left = (self.motor_multiplier * power_left) / 100
            power_right = (self.motor_multiplier * power_right) / 100
        
            # Print the converted values out for debug
            # print("left: {}".format(power_left))
            # print("right: {}".format(power_right))
        
            # If power is less than 0, we want to turn the motor backwards, otherwise turn it forwards
            
            if power_left < 0:
                #print("power_left ",power_left)
                self.frontLeft.forward(-power_left)
                self.rearLeft.forward(-power_left) 
            else:
                #print("power_left ",power_left)
                self.frontLeft.backward(power_left)
                self.rearLeft.backward(power_left)
        
            if power_right < 0:
                self.frontRight.forward(-power_right)
                self.rearRight.forward(-power_right)
            else:
                self.frontRight.backward(power_right)
                self.rearRight.backward(power_right)
        
        def stop_motors(self):
            """
            As we have a motor hat, stop the motors using their motors call
            """
            # Turn both motors off
            self.frontLeft.stop()
            self.frontRight.stop()
            self.rearLeft.stop()
            self.rearRight.stop()
            
    robot = MecRobot()
     
# All we need, as we don't care which controller we bind to, is the ControllerResource
from approxeng.input.selectbinder import ControllerResource

'''
 robot based on camjam edu kit  and approx eng software
controller has following controls
{'axes': 
    ['l', this is lx,ly as a tuple
    'lt', UNUSED
    'lx', turn left right
    'ly', forwards backwards speed
    'r', rx,ry as a tuple
    'rt', UNUSED
    'rx', UNUSED
    'ry',  
    ], 
'buttons': 
   ['circle', toggle line following mode
   'cross', 
   'ddown', UNUSED
   'dleft', 
   'dright', 
   'dup', UNUSED
   'home', labelled analog stops program
   'l1', 
   'ls', ?
   'r1', 
   'rs', ?
   'select', UNUSED
   'square', 
   'start', shuits down raspberry pi
   'triangle'  UNUSED
   ]}
['cross']

                      
'''


class RobotStopException(Exception):
    """
    The simplest possible subclass of Exception, we'll raise this if we want to stop the robot
    for any reason. Creating a custom exception like this makes the code more readable later.
    """
    pass
    
    
   
class RobotLoop():
    
    def __init__(self,arobot):
        self.robot = arobot
            
    def mixer(self,yaw, throttle, max_power=100):
        """
        Mix a pair of joystick axes, returning a pair of wheel speeds. This is where the mapping from
        joystick positions to wheel powers is defined, so any changes to how the robot drives should
        be made here, everything else is really just plumbing.
        
        :param yaw: 
            Yaw axis value, ranges from -1.0 to 1.0
        :param throttle: 
            Throttle axis value, ranges from -1.0 to 1.0
        :param max_power: 
            Maximum speed that should be returned from the mixer, defaults to 100
        :return: 
            A pair of power_left, power_right integer values to send to the motor driver
        """
        left = throttle + yaw
        right = throttle - yaw
        scale = float(max_power) / max(1, abs(left), abs(right))
        return int(left * scale), int(right * scale)
    
    def processLoop(self,time2Go):
        allFinished = False

        followLine = False
        lineFollowSpeed = 1.0
        lineFollowGain = 2.0
        time2UpdateLineError = time.time()
        errorThreshold = 0.01
        # Outer try / except catches the RobotStopException we just defined, which we'll raise when we want to
        # bail out of the loop cleanly, shutting the motors down. We can raise this in response to a button press
        try:
            while True:
                # Inner try / except is used to wait for a controller to become available, at which point we
                # bind to it and enter a loop where we read axis values and send commands to the motors.
                try:
                    # Bind to any available joystick, this will use whatever's connected as long as the library
                    # supports it.
                    with ControllerResource(dead_zone=0.1, hot_zone=0.2) as joystick:
                        print('Controller found, press HOME button to exit, use left stick to drive.')
                        print(joystick.controls)
                        # Loop until the joystick disconnects, or we deliberately stop by raising a
                        # RobotStopException
                        while joystick.connected:                       
                            tstart = time.time()
                            joystick.check_presses()
                            # Print out any buttons that were pressed, if we had any
                            #if joystick.has_presses:
                            #    print(joystick.presses)
                            # If home was pressed, raise a RobotStopException to bail out of the loop
                            # Home is generally the PS button for playstation controllers, XBox for XBox etc
                            if 'home' in joystick.presses:
                                raise RobotStopException()
                            elif 'start' in joystick.presses:
                                allFinished  = True
                                raise RobotStopException()
                            elif 'circle' in joystick.presses:
                                followLine = not followLine
                                #print("followline ",followLine)
                            elif 'triangle' in joystick.presses:
                                lineFollowSpeed += 0.05
                                if lineFollowSpeed > 0.99:
                                    lineFollowSpeed = 1.0
                                print(lineFollowSpeed)
                            elif 'dup' in joystick.presses:
                                lineFollowGain+= 0.5
                                print(lineFollowGain)
                            elif 'ddown' in joystick.presses:
                                lineFollowGain-= 0.5
                                if lineFollowGain < 1.0:
                                    lineFollowGain = 1.0
                                print(lineFollowGain)
                            
                            # now process command
                            
 
                            if not followLine:
                                # Get joystick values from the left analogue stick
                                x_axis, y_axis = joystick['lx', 'ly']
                                # Get power from mixer function
                                #print(x_axis, y_axis)
                                power_left, power_right = self.mixer(yaw=x_axis, throttle=y_axis)
                                # Set motor speeds
                                
                                self.robot.set_speeds(power_left, power_right)
                                
                            else:
                                endpoint = 'http://127.0.0.1:8000/lineError'
                                lineError = 0.0
                                if time.time() > time2UpdateLineError:
                                    try:
                                        response = requests.get(endpoint)
                                        lineError = float(response.text)
                                        if lineError < -1:
                                            followLine = False # stop
                                    except:
                                        print("No response")
                                        pass
                                    time2UpdateLineError = time.time() + 0.05 #0.1 # only get line error at 10Hz
                                    if abs(lineError) > errorThreshold:
                                        yaw = lineError  * lineFollowGain
                                        #print(yaw)
                                    else:
                                        # now set speeds wants demand sabetween 0 and 100, lineFollowSpeed is between 0 and 1
                                        # so multiply by 100
                                        #forwardSpeed = lineFollowSpeed * 100
                                        yaw = 0
                                        #print("F")
                                    power_left, power_right = self.mixer(yaw, throttle=lineFollowSpeed)
                                    self.robot.set_speeds(power_left, power_right)
                                    #print(lineError,diagSpeed, lineFollowGain)

                            loopTime = (time.time() - tstart)
                            sleepTime = 0.02 - loopTime # run at 50Hz
                            if sleepTime > 0:
                                sleep(sleepTime)
                            else:
                                sleep(0.02)
                                #print(loopTime)
                except IOError:
                    # We get an IOError when using the ControllerResource if we don't have a controller yet,
                    # so in this case we just wait a second and try again after printing a message.
                    print('No controller found yet')
                    sleep(1)
        except RobotStopException:
            # This exception will be raised when the home button is pressed, at which point we should
            # stop the motors.
            self.robot.stop_motors()
            if allFinished:
                os.system("sudo shutdown -h now")
                print("going down")
            else:
                print("quit")
                time2Go = True
                self.robot.red.off()

if __name__ == '__main__':
    import sys
    piwars =RobotLoop(robot)
    time2Go = False
    piwars.processLoop(time2Go)
 
