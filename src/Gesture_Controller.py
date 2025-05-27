# gesture_controller.py

# Imports
import cv2
import mediapipe as mp
import pyautogui
import math
from enum import IntEnum
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from google.protobuf.json_format import MessageToDict
import screen_brightness_control as sbcontrol

pyautogui.FAILSAFE = False
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Gesture Encodings
class Gest(IntEnum):
    # Binary Encoded
    """
    Enum for mapping all hand gesture to binary number.
    """
    FIST = 0
    PINKY = 1
    RING = 2
    MID = 4
    LAST3 = 7
    INDEX = 8
    FIRST2 = 12
    LAST4 = 15
    THUMB = 16    
    PALM = 31
    
    # Extra Mappings
    V_GEST = 33
    TWO_FINGER_CLOSED = 34
    PINCH_MAJOR = 35
    PINCH_MINOR = 36

# Multi-handedness Labels
class HLabel(IntEnum):
    MINOR = 0
    MAJOR = 1

# Convert Mediapipe Landmarks to recognizable Gestures
class HandRecog:
    """
    Convert Mediapipe Landmarks to recognizable Gestures.
    """
    
    def __init__(self, hand_label):
        """
        Constructs all the necessary attributes for the HandRecog object.

        Parameters
        ----------
            finger : int
                Represent gesture corresponding to Enum 'Gest',
                stores computed gesture for current frame.
            ori_gesture : int
                Represent gesture corresponding to Enum 'Gest',
                stores gesture being used.
            prev_gesture : int
                Represent gesture corresponding to Enum 'Gest',
                stores gesture computed for previous frame.
            frame_count : int
                total no. of frames since 'ori_gesture' is updated.
            hand_result : Object
                Landmarks obtained from mediapipe.
            hand_label : int
                Represents multi-handedness corresponding to Enum 'HLabel'.
        """

        self.finger = 0
        self.ori_gesture = Gest.PALM
        self.prev_gesture = Gest.PALM
        self.frame_count = 0
        self.hand_result = None
        self.hand_label = hand_label
    
    def update_hand_result(self, hand_result):
        self.hand_result = hand_result

    def get_signed_dist(self, point):
        """
        returns signed euclidean distance between 'point'.

        Parameters
        ----------
        point : list containing two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        sign = -1
        if self.hand_result.landmark[point[0]].y < self.hand_result.landmark[point[1]].y:
            sign = 1
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist*sign
    
    def get_dist(self, point):
        """
        returns euclidean distance between 'point'.

        Parameters
        ----------
        point : list containing two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist
    
    def get_dz(self,point):
        """
        returns absolute difference on z-axis between 'point'.

        Parameters
        ----------
        point : list containing two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        return abs(self.hand_result.landmark[point[0]].z - self.hand_result.landmark[point[1]].z)
    
    # Function to find Gesture Encoding using current finger_state.
    # Finger_state: 1 if finger is open, else 0
    def set_finger_state(self):
        """
        set 'finger' by computing ratio of distance between finger tip 
        , middle knuckle, base knuckle.

        Returns
        -------
        None
        """
        if self.hand_result == None:
            return

        points = [[8,5,0],[12,9,0],[16,13,0],[20,17,0]]
        self.finger = 0
        self.finger = self.finger | 0 #thumb
        for idx,point in enumerate(points):
            
            dist = self.get_signed_dist(point[:2])
            dist2 = self.get_signed_dist(point[1:])
            
            try:
                ratio = round(dist/dist2,1)
            except:
                ratio = round(dist/0.01,1)

            self.finger = self.finger << 1
            if ratio > 0.5 :
                self.finger = self.finger | 1
    

    # Handling Fluctuations due to noise
    def get_gesture(self):
        """
        returns int representing gesture corresponding to Enum 'Gest'.
        sets 'frame_count', 'ori_gesture', 'prev_gesture', 
        handles fluctuations due to noise.
        
        Returns
        -------
        int
        """
        if self.hand_result == None:
            return Gest.PALM

        current_gesture = Gest.PALM
        if self.finger in [Gest.LAST3,Gest.LAST4] and self.get_dist([8,4]) < 0.05:
            if self.hand_label == HLabel.MINOR :
                current_gesture = Gest.PINCH_MINOR
            else:
                current_gesture = Gest.PINCH_MAJOR

        elif Gest.FIRST2 == self.finger :
            point = [[8,12],[5,9]]
            dist1 = self.get_dist(point[0])
            dist2 = self.get_dist(point[1])
            ratio = dist1/dist2
            if ratio > 1.7:
                current_gesture = Gest.V_GEST
            else:
                if self.get_dz([8,12]) < 0.1:
                    current_gesture =  Gest.TWO_FINGER_CLOSED
                else:
                    current_gesture =  Gest.MID
            
        else:
            current_gesture =  self.finger
        
        if current_gesture == self.prev_gesture:
            self.frame_count += 1
        else:
            self.frame_count = 0

        self.prev_gesture = current_gesture

        if self.frame_count > 4 :
            self.ori_gesture = current_gesture
        return self.ori_gesture

# Executes commands according to detected gestures
class Controller:
    """
    Executes commands according to detected gestures.

    Attributes
    ----------
    tx_old : int
        previous mouse location x coordinate
    ty_old : int
        previous mouse location y coordinate
    flag : bool
        true if V gesture is detected
    grabflag : bool
        true if FIST gesture is detected
    pinchmajorflag : bool
        true if PINCH gesture is detected through MAJOR hand,
        on x-axis 'Controller.changesystembrightness', 
        on y-axis 'Controller.changesystemvolume'.
    pinchminorflag : bool
        true if PINCH gesture is detected through MINOR hand,
        on x-axis 'Controller.scrollHorizontal', 
        on y-axis 'Controller.scrollVertical'.
    pinchstartxcoord : int
        x coordinate of hand landmark when pinch gesture is started.
    pinchstartycoord : int
        y coordinate of hand landmark when pinch gesture is started.
    pinchdirectionflag : bool
        true if pinch gesture movement is along x-axis,
        otherwise false
    prevpinchlv : int
        stores quantized magnitude of prev pinch gesture displacement, from 
        starting position
    pinchlv : int
        stores quantized magnitude of pinch gesture displacement, from 
        starting position
    framecount : int
        stores no. of frames since 'pinchlv' is updated.
    prev_hand : tuple
        stores (x, y) coordinates of hand in previous frame.
    pinch_threshold : float
        step size for quantization of 'pinchlv'.
    """

    tx_old = 0
    ty_old = 0
    trial = True
    flag = False
    grabflag = False
    pinchmajorflag = False
    pinchminorflag = False
    pinchstartxcoord = None
    pinchstartycoord = None
    pinchdirectionflag = None
    prevpinchlv = 0
    pinchlv = 0
    framecount = 0
    prev_hand = None
    pinch_threshold = 0.3
    
    @staticmethod
    def getpinchylv(hand_result):
        """returns distance between starting pinch y coord and current hand position y coord."""
        dist = round((Controller.pinchstartycoord - hand_result.landmark[8].y)*10,1)
        return dist

    @staticmethod
    def getpinchxlv(hand_result):
        """returns distance between starting pinch x coord and current hand position x coord."""
        dist = round((hand_result.landmark[8].x - Controller.pinchstartxcoord)*10,1)
        return dist
    
    @staticmethod
    def changesystembrightness():
        """sets system brightness based on 'Controller.pinchlv'."""
        currentBrightnessLv = sbcontrol.get_brightness(display=0)/100.0
        currentBrightnessLv += Controller.pinchlv/50.0
        if currentBrightnessLv > 1.0:
            currentBrightnessLv = 1.0
        elif currentBrightnessLv < 0.0:
            currentBrightnessLv = 0.0       
        sbcontrol.fade_brightness(int(100*currentBrightnessLv) , start = sbcontrol.get_brightness(display=0))
    
    @staticmethod
    def changesystemvolume():
        """sets system volume based on 'Controller.pinchlv'."""
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        currentVolumeLv = volume.GetMasterVolumeLevelScalar()
        currentVolumeLv += Controller.pinchlv/50.0
        if currentVolumeLv > 1.0:
            currentVolumeLv = 1.0
        elif currentVolumeLv < 0.0:
            currentVolumeLv = 0.0
        volume.SetMasterVolumeLevelScalar(currentVolumeLv, None)

    @staticmethod
    def scrollVertical(level):
        """scrolls vertically by amount 'level'."""
        pyautogui.scroll(level * 120)  

    @staticmethod
    def scrollHorizontal(level):
        """scrolls horizontally by amount 'level'."""
        pyautogui.hscroll(level * 120)
        
    @staticmethod
    def mouse_move(x, y):
        pyautogui.moveTo(x, y)

    @staticmethod
    def mouse_drag(x, y):
        pyautogui.dragTo(x, y, button='left')

    @staticmethod
    def left_click():
        pyautogui.click(button='left')

    @staticmethod
    def right_click():
        pyautogui.click(button='right')

    @staticmethod
    def pinch_handler(hand_label, hand_result, ori_gesture):
        """Handles pinch gestures on major and minor hands."""
        if ori_gesture == Gest.PINCH_MAJOR:
            if not Controller.pinchmajorflag:
                Controller.pinchmajorflag = True
                Controller.pinchstartxcoord = hand_result.landmark[8].x
                Controller.pinchstartycoord = hand_result.landmark[8].y
                Controller.prevpinchlv = 0
                Controller.pinchlv = 0
                Controller.framecount = 0
            else:
                if Controller.pinchdirectionflag is None:
                    delta_x = abs(hand_result.landmark[8].x - Controller.pinchstartxcoord)
                    delta_y = abs(hand_result.landmark[8].y - Controller.pinchstartycoord)
                    Controller.pinchdirectionflag = (delta_x > delta_y)
                if Controller.pinchdirectionflag:
                    Controller.pinchlv = Controller.getpinchxlv(hand_result)
                else:
                    Controller.pinchlv = Controller.getpinchylv(hand_result)
                if abs(Controller.pinchlv - Controller.prevpinchlv) > Controller.pinch_threshold:
                    if Controller.pinchdirectionflag:
                        Controller.changesystembrightness()
                    else:
                        Controller.changesystemvolume()
                    Controller.prevpinchlv = Controller.pinchlv

        else:
            Controller.pinchmajorflag = False
            Controller.pinchdirectionflag = None

        if ori_gesture == Gest.PINCH_MINOR:
            if not Controller.pinchminorflag:
                Controller.pinchminorflag = True
                Controller.pinchstartxcoord = hand_result.landmark[8].x
                Controller.pinchstartycoord = hand_result.landmark[8].y
                Controller.prevpinchlv = 0
                Controller.pinchlv = 0
                Controller.framecount = 0
            else:
                if Controller.pinchdirectionflag is None:
                    delta_x = abs(hand_result.landmark[8].x - Controller.pinchstartxcoord)
                    delta_y = abs(hand_result.landmark[8].y - Controller.pinchstartycoord)
                    Controller.pinchdirectionflag = (delta_x > delta_y)
                if Controller.pinchdirectionflag:
                    Controller.pinchlv = Controller.getpinchxlv(hand_result)
                else:
                    Controller.pinchlv = Controller.getpinchylv(hand_result)
                if abs(Controller.pinchlv - Controller.prevpinchlv) > Controller.pinch_threshold:
                    if Controller.pinchdirectionflag:
                        Controller.scrollHorizontal(int(Controller.pinchlv))
                    else:
                        Controller.scrollVertical(int(Controller.pinchlv))
                    Controller.prevpinchlv = Controller.pinchlv
        else:
            Controller.pinchminorflag = False
            Controller.pinchdirectionflag = None
    
    @staticmethod
    def process(hand_label, hand_result, gesture):
        """
        Processes gesture commands for the hand.

        Parameters
        ----------
        hand_label : int
            Label indicating which hand (HLabel.MINOR or HLabel.MAJOR)
        hand_result : mediapipe hand landmarks object
        gesture : int
            Gesture from Gest Enum
        
        Returns
        -------
        None
        """
        # Handle pinch gestures first (for volume/brightness and scrolling)
        Controller.pinch_handler(hand_label, hand_result, gesture)

        # Get current hand x,y coordinates (index finger tip)
        x = int(hand_result.landmark[8].x * pyautogui.size().width)
        y = int(hand_result.landmark[8].y * pyautogui.size().height)

        # Store previous coordinates for reference
        if Controller.prev_hand is None:
            Controller.prev_hand = (x, y)

        # If gesture is FIST, drag mouse
        if gesture == Gest.FIST:
            if not Controller.grabflag:
                Controller.grabflag = True
                Controller.tx_old = x
                Controller.ty_old = y
                pyautogui.mouseDown()
            else:
                dx = x - Controller.tx_old
                dy = y - Controller.ty_old
                Controller.tx_old = x
                Controller.ty_old = y
                pyautogui.moveRel(dx, dy)
        else:
            if Controller.grabflag:
                Controller.grabflag = False
                pyautogui.mouseUp()

        # If gesture is V_GEST, left click once
        if gesture == Gest.V_GEST:
            if not Controller.flag:
                Controller.flag = True
                Controller.left_click()
        else:
            Controller.flag = False

        # If gesture is PALM, right click once
        if gesture == Gest.PALM:
            Controller.right_click()
        
        # Update previous hand position
        Controller.prev_hand = (x, y)
