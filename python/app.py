from PyQt5 import QtCore, QtGui, QtWidgets
import RPi.GPIO as GPIO
import time
from picamera import PiCamera
import os
import datetime
import json
from fractions import Fraction

# Variables and Initialization
camera = PiCamera()
camera.resolution = (4056, 3040)

imageExtension = ".jpg"
imageOutputType = "jpeg"
path = os.getcwd()
print ("The current working directory is %s" % path)
projectName = "shot"

# Drive Wheel pins
cw_pin = 26
ccw_pin = 19

# Stack Rig Motor GPIO pins
in1_2 = 17
in2_2 = 27
in3_2 = 22
in4_2 = 23

# Light Control Pin (High to turn on)
lightPin = 21
lightsOn = False

# GPIO setup
GPIO.setmode(GPIO.BCM) 
GPIO.setwarnings(False)

# PiCam stepper pin init
GPIO.setup(in1_2, GPIO.OUT)
GPIO.setup(in2_2, GPIO.OUT)
GPIO.setup(in3_2, GPIO.OUT)
GPIO.setup(in4_2, GPIO.OUT)

# Drive Wheel Motor pin init
GPIO.setup(cw_pin, GPIO.OUT)
GPIO.setup(ccw_pin, GPIO.OUT)
GPIO.output(cw_pin, GPIO.LOW)
GPIO.output(ccw_pin, GPIO.LOW)

# Lights Relay
GPIO.setup(lightPin, GPIO.OUT)
    
# Global Camera Settings (Defaults)
brightness = 50
contrast = 0
awb_mode = 'auto'
awb_gains = 1.1
iso = 200
framerate = '30fps'
shutter_speed = 'auto'
direction = 'Clockwise'

# Global variables to keep track of positions
sliderPosition = 0
turnTablePosition = 0

# Sleep and pauses
sleepTime = 0.002 #time in between motor steps PiCam stepper
shotPause = 2 # time (sec) between motor moves and shots - to settle camera

# Global counters -- apply to both PiCam and DSLR routines
shotNumber = 1 #counter for naming shots in stack sequentially
testShotNumber = 1 #counter for naming test shots
stackNumber = 1 # counter for folder naming in full routine

# Default Step Cycles and values
dollyMovement = 5 # default number of PWM cycles for the turntable in one motion segment (change these with respective sliders)

arcLength = 360 # Total degrees traveled. Divide by dollyMovement to get numberStacks
cameraMovement = 10 # default number of PWM cycles for the focus rack in one motion segment 

numberShots = 20 # default number of shots in each stack
numberStacks = 72 # default number of stacks in the routine

# Raspberry Pi HQ Camera Slider
def forward():
    global cameraMovement
    print("Your camera is moving forward in " + str(cameraMovement) + " step increments")
    global sliderPosition
    sliderPosition += cameraMovement
    segment = cameraMovement
    print("Slider Position: " + str(sliderPosition))
    while (segment > 0):
        GPIO.output(in1_2, GPIO.HIGH)
        GPIO.output(in2_2, GPIO.LOW)
        GPIO.output(in3_2, GPIO.LOW)
        GPIO.output(in4_2, GPIO.LOW)
        time.sleep(sleepTime)
        GPIO.output(in1_2, GPIO.LOW)
        GPIO.output(in2_2, GPIO.HIGH)
        GPIO.output(in3_2, GPIO.LOW)
        GPIO.output(in4_2, GPIO.LOW)
        time.sleep(sleepTime)
        GPIO.output(in1_2, GPIO.LOW)
        GPIO.output(in2_2, GPIO.LOW)
        GPIO.output(in3_2, GPIO.HIGH)
        GPIO.output(in4_2, GPIO.LOW)
        time.sleep(sleepTime)
        GPIO.output(in1_2, GPIO.LOW)
        GPIO.output(in2_2, GPIO.LOW)
        GPIO.output(in3_2, GPIO.LOW)
        GPIO.output(in4_2, GPIO.HIGH)
        time.sleep(sleepTime)
        segment -= 1
    disableMotors()
    ui.location_value_lbl.setText(str(sliderPosition))
    
def reverse():
    global cameraMovement
    print("Your camera is moving in reverse in " + str(cameraMovement) + " step increments")
    global sliderPosition
    sliderPosition -= cameraMovement
    print("Slider Position: " + str(sliderPosition))
    segment = cameraMovement
    while (segment > 0):
        GPIO.output(in1_2, GPIO.LOW)
        GPIO.output(in2_2, GPIO.LOW)
        GPIO.output(in3_2, GPIO.LOW)
        GPIO.output(in4_2, GPIO.HIGH)
        time.sleep(sleepTime)
        GPIO.output(in1_2, GPIO.LOW)
        GPIO.output(in2_2, GPIO.LOW)
        GPIO.output(in3_2, GPIO.HIGH)
        GPIO.output(in4_2, GPIO.LOW)
        time.sleep(sleepTime)
        GPIO.output(in1_2, GPIO.LOW)
        GPIO.output(in2_2, GPIO.HIGH)
        GPIO.output(in3_2, GPIO.LOW)
        GPIO.output(in4_2, GPIO.LOW)
        time.sleep(sleepTime)
        GPIO.output(in1_2, GPIO.HIGH)
        GPIO.output(in2_2, GPIO.LOW)
        GPIO.output(in3_2, GPIO.LOW)
        GPIO.output(in4_2, GPIO.LOW)
        time.sleep(sleepTime)
        segment -= 1
    disableMotors()
    ui.location_value_lbl.setText(str(sliderPosition))

def goHome(): # PiCam slider moves back to 0
    global sliderPosition
    global cameraMovement
    temp = cameraMovement
    cameraMovement = sliderPosition
    reverse()
    cameraMovement = temp
    ui.location_value_lbl.setText(str(sliderPosition))
    print("PiCam is moved back to HOME")
    
def setHome(): # Sets the current PiCam slider position as 'home'
    global sliderPosition
    sliderPosition = 0
    ui.location_value_lbl.setText(str(sliderPosition))
    print("The current position of the PiCam is now the home position")

# Drive Wheel Functionality
def driveCW():
    global dollyMovement
    seconds = dollyMovement /2
    GPIO.output(cw_pin, GPIO.HIGH)
    time.sleep(seconds)
    GPIO.output(cw_pin, GPIO.LOW)
    
def driveCCW():
    global dollyMovement
    seconds = dollyMovement / 2
    GPIO.output(ccw_pin, GPIO.HIGH)
    time.sleep(seconds)
    GPIO.output(ccw_pin, GPIO.LOW)

def disableMotors(): # Turns off the current to motors while they are not moving, decreases holding power, but keeps everything cool. *you should actually run this at boot, with the accompanying script
    GPIO.output(in1_2, GPIO.LOW)
    GPIO.output(in2_2, GPIO.LOW)
    GPIO.output(in3_2, GPIO.LOW)
    GPIO.output(in4_2, GPIO.LOW)
    print("Motors are disabled")


# Camera Stuff
# If the preview causes display issues, you can increase GPU memory or use a smaller PiCam Resolution
def camPreviewWindowed(): 
    camera.start_preview(fullscreen=False, window=(600,150,1024,576))
    
def camStopPreview():
    camera.stop_preview()

def testShot(): # Doesn't screw up the shot count for full routine
    global path
    global testShotNumber
    global imageExtension
    global imageOutputType
    if not os.path.exists('testShots'):
        os.makedirs('testShots')
    camera.capture(path + "/testShots/testShot_" + str(testShotNumber) + str(imageExtension), str(imageOutputType))
    testShotNumber += 1

def shoot(): # PiCam - capture single photo
    global path
    global shotNumber
    global imageExtension
    global imageOutputType
    global projectName
    print("PiCam shot #" + str(shotNumber))
    if (shotNumber < 10):
        camera.capture(path + "/" + projectName + "0" + str(shotNumber) + str(imageExtension), str(imageOutputType))
    else:
        camera.capture(path + "/" + projectName + str(shotNumber) + str(imageExtension), str(imageOutputType))
    shotNumber += 1

def runStackRoutine(): # With current settings 
    global projectName
    global stackNumber
    global path
    newPath = projectName + "_" + str(stackNumber)
    os.mkdir(newPath)
    path = newPath
    
    global numberShots
    for x in range(0,numberShots):
        shoot()
        time.sleep(shotPause)
        forward()
        time.sleep(shotPause)
    print("PiCam done with stack #" + str(stackNumber))
    stackNumber += 1
    resetShotNumber()

def runFullRoutine():
    setHome()
    global direction
    global camera
    global numberStacks
    global numberShots
    print("PiCam Full Routine Started!")
    print(str(numberStacks)+" stacks of " + str(numberShots) + " shots")
    for x in range(0,numberStacks):
        runStackRoutine()
        if direction == "Clockwise":
            driveCW()
        elif direction == "Counter-Clockwise":
            driveCCW()
        goHome()

# Camera Settings Adjustment Methods

def changeFramerate(combo_value):
    global camera
    if combo_value == '30fps':
        camera.framerate = Fraction(30,1)
    elif combo_value == '1fps':
        camera.framerate = 1
    elif combo_value == '1/2fps':
        camera.framerate = Fraction(1,2)
    elif combo_value == '1/3fps':
        camera.framerate = Fraction(1,3)
    else:
        camera.framerate = 'auto'
    
    
def changeShutterSpeed(combo_value):
    global camera
    if combo_value == '1/500':
        camera.shutter_speed = 2000
    elif combo_value == '1/250':
        camera.shutter_speed = 4000
    elif combo_value == '1/125':
        camera.shutter_speed = 8000
    elif combo_value == '1/60':
        camera.shutter_speed = 16666
    elif combo_value == '1/30':
        camera.shutter_speed = 33333
    elif combo_value == '1/15':
        camera.shutter_speed = 66666
    elif combo_value == '1/8':
        camera.shutter_speed = 125000
    elif combo_value == '1/4':
        camera.shutter_speed = 250000
    elif combo_value == '1/2':
        camera.shutter_speed = 500000
    elif combo_value == '1 second':
        camera.shutter_speed = 1000000
    elif combo_value == '2 seconds':
        camera.shutter_speed = 2000000
    elif combo_value == '3 seconds':
        camera.shutter_speed = 3000000
    else: combo_value == 'auto'
    print("Shutter Speed is set to " + combo_value)   


# Utility Methods
def resetShotNumber(): #Not used in UI -- used inside routine
    global shotNumber
    shotNumber = 1
    print("Shot count is reset to 1")

def exportSettings():
    global brightness
    global contrast
    global awb_mode
    global awb_gains
    global iso
    global framerate
    global shutter_speed
    global dollyMovement
    global cameraMovement
    global arcLength
    global numberShots
    global numberStacks
    global direction

    myDict = {
        "Brightness": brightness,
        "Contrast": contrast,
        "AWB Mode": awb_mode,
        "AWB Gains": awb_gains,
        "ISO": iso,
        "Framerate": framerate,
        "Shutter Speed": shutter_speed,
        "Project Name": projectName,
        "Camera Movement": cameraMovement,
        "Dolly Movement": dollyMovement,
        "Arc Length": arcLength,
        "Number of Shots in Stack": numberShots,
        "Number of Stacks": numberStacks,
        "Direction": direction
    }
    
    x = datetime.datetime.now()
    timestamp = x.strftime('%b%d_%I:%M%p')

    with open('exported-settings' + timestamp + '.json', 'w') as f:
    
        f.write(json.dumps(myDict, indent=4))

def loadDefaultSettings():
    global brightness
    global contrast
    global awb_mode
    global awb_gains
    global iso
    global framerate
    global shutter_speed
    global dollyMovement
    global cameraMovement
    global arcLength
    global numberShots
    global numberStacks
    global direction

    with open('defaults.json') as f:
        defaults = json.load(f)
       
    

    brightness = defaults["Brightness"]
    ui.brightness_input.setText(str(brightness))
    ui.brightness_slider.setValue(brightness)
    contrast = defaults["Contrast"]
    ui.contrast_input.setText(str(contrast))
    ui.contrast_slider.setValue(contrast)
    awb_mode = defaults["AWB Mode"]
    ui.awb_mode_combo.setCurrentText(awb_mode)
    awb_gains = defaults["AWB Gains"]
    ui.awb_gains_input.setText(str(awb_gains))
    ui.awb_gains_slider.setValue(awb_gains)
    iso = defaults["ISO"]
    ui.iso_input.setText(str(iso))
    ui.iso_slider.setValue(iso)
    framerate = defaults["Framerate"]
    ui.framerate_combo.setCurrentText(framerate)
    shutter_speed = defaults["Shutter Speed"]
    ui.shutter_speed_combo.setCurrentText(shutter_speed)
    dollyMovement = defaults["Dolly Movement"]
    ui.dolly_movement_input.setText(str(dollyMovement))
    ui.dolly_movement_slider.setValue(dollyMovement)
    cameraMovement = defaults["Camera Movement"]
    ui.camera_movement_input.setText(str(cameraMovement))
    ui.camera_movement_slider.setValue(cameraMovement)
    arcLength = defaults["Arc Length"]
    ui.arc_length_input.setText(str(arcLength))
    ui.arc_length_slider.setValue(arcLength)
    numberShots = defaults["Number of Shots in Stack"]
    ui.num_shots_input.setText(str(numberShots))
    ui.num_shots_slider.setValue(numberShots)
    numberStacks = defaults["Number of Stacks"]
    direction = defaults["Direction"]
    ui.direction_combo.setCurrentText(direction)





def calculateNumberStacks():
    global numberStacks
    global arcLength
    global dollyMovement
    numberStacks = arcLength / dollyMovement



class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(390, 876)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)
        
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 390, 18))
        self.menubar.setObjectName("menubar")
        
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        
        MainWindow.setStatusBar(self.statusbar)
        
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)


        # Brightness Slider Construction
        self.brightness_lbl = QtWidgets.QLabel(self.centralwidget)
        self.brightness_lbl.setGeometry(QtCore.QRect(20, 20, 101, 21))
        self.brightness_lbl.setObjectName("brightness_lbl")
        
        self.brightness_slider = QtWidgets.QSlider(self.centralwidget)
        self.brightness_slider.setGeometry(QtCore.QRect(170, 20, 151, 21))
        self.brightness_slider.setOrientation(QtCore.Qt.Horizontal)
        self.brightness_slider.setObjectName("brightness_slider")
        self.brightness_slider.setValue(50)
        self.brightness_slider.setMaximum(100)
        self.brightness_slider.valueChanged.connect(self.brightnessSlider_changed)
        
        self.brightness_input = QtWidgets.QLineEdit(self.centralwidget)
        self.brightness_input.setGeometry(QtCore.QRect(329, 19, 41, 20))
        self.brightness_input.setObjectName("brightness_input")
        self.brightness_input.setText("50")
        self.brightness_input.setValidator(QtGui.QIntValidator())
        self.brightness_input.setMaxLength(3)
        self.brightness_input.textChanged.connect(self.brightnessInput_changed)
        
        # Contrast Slider Construction
        self.contrast_lbl = QtWidgets.QLabel(self.centralwidget)
        self.contrast_lbl.setGeometry(QtCore.QRect(20, 60, 101, 21))
        self.contrast_lbl.setObjectName("contrast_lbl")
        
        self.contrast_slider = QtWidgets.QSlider(self.centralwidget)
        self.contrast_slider.setGeometry(QtCore.QRect(170, 60, 151, 21))
        self.contrast_slider.setOrientation(QtCore.Qt.Horizontal)
        self.contrast_slider.setObjectName("contrast_slider")
        self.contrast_slider.setValue(0)
        self.contrast_slider.setMinimum(-100)
        self.contrast_slider.setMaximum(100)
        self.contrast_slider.valueChanged.connect(self.contrastSlider_changed)
        
        self.contrast_input = QtWidgets.QLineEdit(self.centralwidget)
        self.contrast_input.setGeometry(QtCore.QRect(330, 60, 41, 20))
        self.contrast_input.setObjectName("contrast_input")
        self.contrast_input.setText("0")
        #self.contrast_input.setValidator(QtGui.QIntValidator())
        #self.contrast_input.setMaxLength(3)
        self.contrast_input.setReadOnly(True)
        #self.contrast_input.textChanged.connect(self.contrastInput_changed)
        
        # AWB Mode Combo Box Construction
        self.awb_mode_lbl = QtWidgets.QLabel(self.centralwidget)
        self.awb_mode_lbl.setGeometry(QtCore.QRect(20, 100, 101, 21))
        self.awb_mode_lbl.setObjectName("awb_mode_lbl")

        self.awb_mode_combo = QtWidgets.QComboBox(self.centralwidget)
        self.awb_mode_combo.setGeometry(QtCore.QRect(170, 100, 201, 22))
        self.awb_mode_combo.setObjectName("awb_mode_combo")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.addItem("")
        self.awb_mode_combo.currentTextChanged.connect(self.awb_modeCombo_selected)

        # AWB Gains Slider Construction
        self.awb_gains_lbl = QtWidgets.QLabel(self.centralwidget)
        self.awb_gains_lbl.setGeometry(QtCore.QRect(20, 140, 101, 21))
        self.awb_gains_lbl.setObjectName("awb_gains_lbl")
        
        self.awb_gains_slider = QtWidgets.QSlider(self.centralwidget)
        self.awb_gains_slider.setGeometry(QtCore.QRect(170, 140, 151, 21))
        self.awb_gains_slider.setOrientation(QtCore.Qt.Horizontal)
        self.awb_gains_slider.setObjectName("awb_gains_slider")
        self.awb_gains_slider.setMinimum(500)
        self.awb_gains_slider.setMaximum(2500)
        self.awb_gains_slider.setValue(1100)
        self.awb_gains_slider.valueChanged.connect(self.awb_gainsSlider_changed)
        
        self.awb_gains_input = QtWidgets.QLineEdit(self.centralwidget)
        self.awb_gains_input.setGeometry(QtCore.QRect(330, 140, 41, 20))
        self.awb_gains_input.setObjectName("awb_gains_input")
        self.awb_gains_input.setText("1.1")
        self.awb_gains_input.setReadOnly(True)

        # ISO Slider Construction
        self.iso_lbl = QtWidgets.QLabel(self.centralwidget)
        self.iso_lbl.setGeometry(QtCore.QRect(20, 180, 101, 21))
        self.iso_lbl.setObjectName("iso_lbl")
 
        self.iso_slider = QtWidgets.QSlider(self.centralwidget)
        self.iso_slider.setGeometry(QtCore.QRect(170, 180, 151, 21))
        self.iso_slider.setOrientation(QtCore.Qt.Horizontal)
        self.iso_slider.setObjectName("iso_slider")
        self.iso_slider.setValue(200)
        self.iso_slider.setMaximum(1600)
        self.iso_slider.setSingleStep(10)
        self.iso_slider.valueChanged.connect(self.isoSlider_changed)

        self.iso_input = QtWidgets.QLineEdit(self.centralwidget)
        self.iso_input.setGeometry(QtCore.QRect(330, 180, 41, 21))
        self.iso_input.setObjectName("iso_input")
        self.iso_input.setText("200")
        self.iso_input.setValidator(QtGui.QIntValidator())
        self.iso_input.setMaxLength(4)
        self.iso_input.textChanged.connect(self.isoInput_changed)

        # Framerate Combo Box Construction
        self.framerate_lbl = QtWidgets.QLabel(self.centralwidget)
        self.framerate_lbl.setGeometry(QtCore.QRect(20, 220, 101, 21))
        self.framerate_lbl.setObjectName("framerate_lbl")
        
        self.framerate_combo = QtWidgets.QComboBox(self.centralwidget)
        self.framerate_combo.setGeometry(QtCore.QRect(170, 220, 201, 22))
        self.framerate_combo.setObjectName("framerate_combo")
        self.framerate_combo.addItem("")
        self.framerate_combo.addItem("")
        self.framerate_combo.addItem("")
        self.framerate_combo.addItem("")
        self.framerate_combo.currentTextChanged.connect(self.framerateCombo_selected)

        # Shutter Speed Slider Construction
        self.shutter_speed_lbl = QtWidgets.QLabel(self.centralwidget)
        self.shutter_speed_lbl.setGeometry(QtCore.QRect(20, 260, 101, 21))
        self.shutter_speed_lbl.setObjectName("shutter_speed_lbl")
        
        self.shutter_speed_combo = QtWidgets.QComboBox(self.centralwidget)
        self.shutter_speed_combo.setGeometry(QtCore.QRect(170, 260, 201, 22))
        self.shutter_speed_combo.setObjectName("shutter_speed_combo")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.addItem("")
        self.shutter_speed_combo.currentTextChanged.connect(self.shutter_speedCombo_selected)

        # Start Preview Button Construction
        self.start_preview_btn = QtWidgets.QPushButton(self.centralwidget)
        self.start_preview_btn.setGeometry(QtCore.QRect(20, 300, 111, 41))
        self.start_preview_btn.setObjectName("start_preview_btn")
        
        # Stop Preview Button Construction
        self.stop_preview_btn = QtWidgets.QPushButton(self.centralwidget)
        self.stop_preview_btn.setGeometry(QtCore.QRect(140, 300, 111, 41))
        self.stop_preview_btn.setObjectName("stop_preview_btn")

        # Test Shot Button Construction
        self.test_shot_btn = QtWidgets.QPushButton(self.centralwidget)
        self.test_shot_btn.setGeometry(QtCore.QRect(260, 300, 111, 41))
        self.test_shot_btn.setObjectName("test_shot_btn")

        # Project Name Text Input Construction
        self.project_name_lbl = QtWidgets.QLabel(self.centralwidget)
        self.project_name_lbl.setGeometry(QtCore.QRect(20, 360, 141, 21))
        self.project_name_lbl.setObjectName("project_name_lbl")
        
        self.project_name_input = QtWidgets.QLineEdit(self.centralwidget)
        self.project_name_input.setGeometry(QtCore.QRect(170, 360, 201, 20))
        self.project_name_input.setObjectName("project_name_input")
        self.project_name_input.textChanged.connect(self.projectName_fieldChanged)

        # Camera Movement Slider Construction
        self.camera_movement_lbl = QtWidgets.QLabel(self.centralwidget)
        self.camera_movement_lbl.setGeometry(QtCore.QRect(20, 400, 141, 21))
        self.camera_movement_lbl.setObjectName("camera_movement_lbl")
        
        self.camera_movement_slider = QtWidgets.QSlider(self.centralwidget)
        self.camera_movement_slider.setGeometry(QtCore.QRect(170, 400, 151, 21))
        self.camera_movement_slider.setOrientation(QtCore.Qt.Horizontal)
        self.camera_movement_slider.setObjectName("camera_movement_slider")
        self.camera_movement_slider.setMaximum(100)
        self.camera_movement_slider.valueChanged.connect(self.cameraMovementSlider_changed)
        
        self.camera_movement_input = QtWidgets.QLineEdit(self.centralwidget)
        self.camera_movement_input.setGeometry(QtCore.QRect(330, 400, 41, 20))
        self.camera_movement_input.setObjectName("camera_movement_input")
        self.camera_movement_input.setText("10")
        self.camera_movement_input.setValidator(QtGui.QIntValidator())
        self.camera_movement_input.setMaxLength(3)
        self.camera_movement_input.textChanged.connect(self.cameraMovementInput_changed)

        # Camera Reverse Button Construction
        self.camera_reverse_btn = QtWidgets.QPushButton(self.centralwidget)
        self.camera_reverse_btn.setGeometry(QtCore.QRect(20, 440, 171, 41))
        self.camera_reverse_btn.setObjectName("camera_reverse_btn")

        # Camera Forward Button Construction
        self.camera_forward_btn = QtWidgets.QPushButton(self.centralwidget)
        self.camera_forward_btn.setGeometry(QtCore.QRect(200, 440, 171, 41))
        self.camera_forward_btn.setObjectName("camera_forward_btn")

        # Set Home Button Construction
        self.set_home_btn = QtWidgets.QPushButton(self.centralwidget)
        self.set_home_btn.setGeometry(QtCore.QRect(20, 500, 91, 41))
        self.set_home_btn.setObjectName("set_home_btn")

        # Go Home Button Construction
        self.go_home_btn = QtWidgets.QPushButton(self.centralwidget)
        self.go_home_btn.setGeometry(QtCore.QRect(120, 500, 91, 41))
        self.go_home_btn.setObjectName("go_home_btn")

        # Location Readout Construction
        self.location_lbl = QtWidgets.QLabel(self.centralwidget)
        self.location_lbl.setGeometry(QtCore.QRect(220, 500, 71, 41))
        self.location_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.location_lbl.setObjectName("location_lbl")
        
        self.location_value_lbl = QtWidgets.QLabel(self.centralwidget)
        self.location_value_lbl.setGeometry(QtCore.QRect(300, 500, 61, 41))
        self.location_value_lbl.setFont(font)
        self.location_value_lbl.setText(str(sliderPosition))
        self.location_value_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.location_value_lbl.setObjectName("location_value_lbl")

        # Shots in Stack Slider Construction
        self.num_shots_lbl = QtWidgets.QLabel(self.centralwidget)
        self.num_shots_lbl.setGeometry(QtCore.QRect(20, 560, 141, 21))
        self.num_shots_lbl.setObjectName("num_shots_lbl")
        
        self.num_shots_slider = QtWidgets.QSlider(self.centralwidget)
        self.num_shots_slider.setGeometry(QtCore.QRect(170, 560, 151, 21))
        self.num_shots_slider.setOrientation(QtCore.Qt.Horizontal)
        self.num_shots_slider.setObjectName("num_shots_slider")
        self.num_shots_slider.setValue(20)
        self.num_shots_slider.setMaximum(99)
        self.num_shots_slider.valueChanged.connect(self.num_shotsSlider_changed)
        
        self.num_shots_input = QtWidgets.QLineEdit(self.centralwidget)
        self.num_shots_input.setGeometry(QtCore.QRect(330, 560, 41, 20))
        self.num_shots_input.setObjectName("num_shots_input")
        self.num_shots_input.setText("20")
        self.num_shots_input.setMaxLength(2)
        self.num_shots_input.textChanged.connect(self.num_shotsInput_changed)

        # Single Shot Button Construction
        self.single_shot_btn = QtWidgets.QPushButton(self.centralwidget)
        self.single_shot_btn.setGeometry(QtCore.QRect(20, 600, 171, 41))
        self.single_shot_btn.setObjectName("single_shot_btn")

        # Shoot Stack Button Construction        
        self.shoot_stack_btn = QtWidgets.QPushButton(self.centralwidget)
        self.shoot_stack_btn.setGeometry(QtCore.QRect(200, 600, 171, 41))
        self.shoot_stack_btn.setObjectName("shoot_stack_btn")

        # Dolly Movement Slider Construction
        self.dolly_movement_lbl = QtWidgets.QLabel(self.centralwidget)
        self.dolly_movement_lbl.setGeometry(QtCore.QRect(20, 660, 141, 21))
        self.dolly_movement_lbl.setObjectName("dolly_movement_lbl")
        
        self.dolly_movement_slider = QtWidgets.QSlider(self.centralwidget)
        self.dolly_movement_slider.setGeometry(QtCore.QRect(170, 660, 151, 21))
        self.dolly_movement_slider.setOrientation(QtCore.Qt.Horizontal)
        self.dolly_movement_slider.setObjectName("dolly_movement_slider")
        self.dolly_movement_slider.setValue(5)
        self.dolly_movement_slider.setMinimum(1)
        self.dolly_movement_slider.setMaximum(360)
        self.dolly_movement_slider.valueChanged.connect(self.dollyMovementSlider_changed)
        
        self.dolly_movement_input = QtWidgets.QLineEdit(self.centralwidget)
        self.dolly_movement_input.setGeometry(QtCore.QRect(330, 660, 41, 20))
        self.dolly_movement_input.setObjectName("dolly_movement_input")
        self.dolly_movement_input.setText("5")
        self.dolly_movement_input.setMaxLength(3)
        self.dolly_movement_input.textChanged.connect(self.dollyMovementInput_changed)

        # Arc Length Slider Construction
        self.arc_length_lbl = QtWidgets.QLabel(self.centralwidget)
        self.arc_length_lbl.setGeometry(QtCore.QRect(20, 700, 141, 21))
        self.arc_length_lbl.setObjectName("arc_length_lbl")
        
        self.arc_length_slider = QtWidgets.QSlider(self.centralwidget)
        self.arc_length_slider.setGeometry(QtCore.QRect(170, 700, 151, 21))
        self.arc_length_slider.setOrientation(QtCore.Qt.Horizontal)
        self.arc_length_slider.setObjectName("arc_length_slider")
        self.arc_length_slider.setMinimum(0)
        self.arc_length_slider.setMaximum(360)
        self.arc_length_slider.setValue(360)
        self.arc_length_slider.valueChanged.connect(self.arcLengthSlider_changed)
        
        self.arc_length_input = QtWidgets.QLineEdit(self.centralwidget)
        self.arc_length_input.setGeometry(QtCore.QRect(330, 700, 41, 20))
        self.arc_length_input.setObjectName("arc_length_input")
        self.arc_length_input.setText("360")
        self.arc_length_input.setMaxLength(3)
        self.arc_length_input.textChanged.connect(self.arcLengthInput_changed)

        # Direction Combo Box Construction
        self.direction_lbl = QtWidgets.QLabel(self.centralwidget)
        self.direction_lbl.setGeometry(QtCore.QRect(20, 740, 141, 21))
        self.direction_lbl.setObjectName("direction_lbl")
        
        self.direction_combo = QtWidgets.QComboBox(self.centralwidget)
        self.direction_combo.setGeometry(QtCore.QRect(170, 740, 201, 22))
        self.direction_combo.setObjectName("direction_combo")
        self.direction_combo.addItem("")
        self.direction_combo.addItem("")

        # Export Settings Button Construction
        self.export_settings_btn = QtWidgets.QPushButton(self.centralwidget)
        self.export_settings_btn.setGeometry(QtCore.QRect(20, 780, 171, 41))
        self.export_settings_btn.setObjectName("export_settings_btn")

        # Run Full Routine Button Construction
        self.run_full_routine_btn = QtWidgets.QPushButton(self.centralwidget)
        self.run_full_routine_btn.setGeometry(QtCore.QRect(200, 780, 171, 41))
        self.run_full_routine_btn.setObjectName("run_full_routine_btn")

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Scanner Companion 2.0"))
        
        # Start Preview Button Connection
        self.start_preview_btn.setText(_translate("MainWindow", "Start Preview"))
        self.start_preview_btn.clicked.connect(self.startPreview_btnClicked)
        
        # Stop Preview Button Connection
        self.stop_preview_btn.setText(_translate("MainWindow", "Stop Preview"))
        self.stop_preview_btn.clicked.connect(self.stopPreview_btnClicked)

        # Test Shot Button Connection
        self.test_shot_btn.setText(_translate("MainWindow", "Test Shot"))
        self.test_shot_btn.clicked.connect(self.testShot_btnClicked)

        # Camera Reverse Button Connection
        self.camera_reverse_btn.setText(_translate("MainWindow", "Camera Reverse"))
        self.camera_reverse_btn.clicked.connect(self.cameraReverse_btnClicked)

        # Camera Forward Button Connection
        self.camera_forward_btn.setText(_translate("MainWindow", "Camera Forward"))
        self.camera_forward_btn.clicked.connect(self.cameraForward_btnClicked)

        # Set Home Button Connection
        self.set_home_btn.setText(_translate("MainWindow", "Set Home"))
        self.set_home_btn.clicked.connect(self.setHome_btnClicked)

        # Go Home Button Connection
        self.go_home_btn.setText(_translate("MainWindow", "Go Home"))
        self.go_home_btn.clicked.connect(self.goHome_btnClicked)

        # Single Shot Button Connection
        self.single_shot_btn.setText(_translate("MainWindow", "Single Shot"))
        self.single_shot_btn.clicked.connect(self.singleShot_btnClicked)

        # Shoot Stack Button Connection
        self.shoot_stack_btn.setText(_translate("MainWindow", "Shoot Stack"))
        self.shoot_stack_btn.clicked.connect(self.shootStack_btnClicked)

        # Export Settings Button Connection
        self.export_settings_btn.setText(_translate("MainWindow", "Export Settings"))
        self.export_settings_btn.clicked.connect(self.exportSettings_btnClicked)

        # Run Full Routine Button Connection
        self.run_full_routine_btn.setText(_translate("MainWindow", "Run Full Routine"))
        self.run_full_routine_btn.clicked.connect(self.runFullRoutine_btnClicked)

        # Labels
        self.brightness_lbl.setText(_translate("MainWindow", "Brightness"))
        #self.brightness_lbl.setStatusTip(_translate("MainWindow", "Manually adjust brightness")) # Example of tooltip
        
        self.contrast_lbl.setText(_translate("MainWindow", "Contrast"))
        
        self.awb_mode_lbl.setText(_translate("MainWindow", "AWB Mode"))
        self.awb_mode_combo.setItemText(0, _translate("MainWindow", "auto"))
        self.awb_mode_combo.setItemText(1, _translate("MainWindow", "sunlight"))
        self.awb_mode_combo.setItemText(2, _translate("MainWindow", "cloudy"))
        self.awb_mode_combo.setItemText(3, _translate("MainWindow", "shade"))
        self.awb_mode_combo.setItemText(4, _translate("MainWindow", "tungsten"))
        self.awb_mode_combo.setItemText(5, _translate("MainWindow", "fluorescent"))
        self.awb_mode_combo.setItemText(6, _translate("MainWindow", "incandescent"))
        self.awb_mode_combo.setItemText(7, _translate("MainWindow", "flash"))
        self.awb_mode_combo.setItemText(8, _translate("MainWindow", "horizon"))
        self.awb_mode_combo.setItemText(9, _translate("MainWindow", "off"))

        self.awb_gains_lbl.setText(_translate("MainWindow", "AWB Gains"))
        self.awb_gains_lbl.setStatusTip('Only works with AWB Mode off')
        
        self.iso_lbl.setText(_translate("MainWindow", "ISO"))
        
        self.framerate_lbl.setText(_translate("MainWindow", "Framerate"))
        self.framerate_combo.setItemText(0, _translate("MainWindow", "30fps"))
        self.framerate_combo.setItemText(1, _translate("MainWindow", "1fps"))
        self.framerate_combo.setItemText(2, _translate("MainWindow", "1/2fps"))
        self.framerate_combo.setItemText(3, _translate("MainWindow", "1/3fps"))
        
        self.shutter_speed_lbl.setText(_translate("MainWindow", "Shutter Speed"))
        self.shutter_speed_lbl.setStatusTip(_translate("MainWindow", "Constrained by framerate"))
        self.shutter_speed_combo.setItemText(0, _translate("MainWindow", "auto"))
        self.shutter_speed_combo.setItemText(1, _translate("MainWindow", "1/500"))
        self.shutter_speed_combo.setItemText(2, _translate("MainWindow", "1/250"))
        self.shutter_speed_combo.setItemText(3, _translate("MainWindow", "1/125"))
        self.shutter_speed_combo.setItemText(4, _translate("MainWindow", "1/60"))
        self.shutter_speed_combo.setItemText(5, _translate("MainWindow", "1/30"))
        self.shutter_speed_combo.setItemText(6, _translate("MainWindow", "1/15"))
        self.shutter_speed_combo.setItemText(7, _translate("MainWindow", "1/8"))
        self.shutter_speed_combo.setItemText(8, _translate("MainWindow", "1/4"))
        self.shutter_speed_combo.setItemText(9, _translate("MainWindow", "1/2"))
        self.shutter_speed_combo.setItemText(10, _translate("MainWindow", "1 second"))
        self.shutter_speed_combo.setItemText(11, _translate("MainWindow", "2 seconds"))
        self.shutter_speed_combo.setItemText(12, _translate("MainWindow", "3 seconds"))
        
        self.project_name_lbl.setText(_translate("MainWindow", "Project Name"))
        
        self.camera_movement_lbl.setText(_translate("MainWindow", "Camera Movement"))
        
        self.location_lbl.setText(_translate("MainWindow", "Location"))
        self.location_value_lbl.setText(_translate("MainWindow", "0"))        # Value - only dynamic label
        
        self.num_shots_lbl.setText(_translate("MainWindow", "# Shots in Stack"))
        
        self.dolly_movement_lbl.setText(_translate("MainWindow", "Dolly Movement"))
        
        self.arc_length_lbl.setText(_translate("MainWindow", "Arc Length"))
        
        self.direction_lbl.setText(_translate("MainWindow", "Direction"))
        self.direction_combo.setItemText(0, _translate("MainWindow", "Clockwise"))
        self.direction_combo.setItemText(1, _translate("MainWindow", "Counter-Clockwise"))

    # Brightness Adjustment Methods
    def brightnessSlider_changed(self):
        global brightness
        brightness = int(self.brightness_slider.value())
        self.brightness_input.setText(str(brightness))
        camera.brightness = brightness

    def brightnessInput_changed(self):
        global brightness
        if self.brightness_input.text():
            brightness = int(self.brightness_input.text())
            self.brightness_slider.setValue(brightness)
            camera.brightness = brightness
        else: 
            self.brightness_input.setText('0')

    # Contrast Adjustment Methods
    def contrastSlider_changed(self):
        global contrast
        contrast = int(self.contrast_slider.value())
        self.contrast_input.setText(str(contrast))
        camera.contrast = contrast

    def contrastInput_changed(self):
        global contrast
        if self.contrast_input.text():
            contrast = int(self.contrast_input.text())
            self.contrast_slider.setValue(contrast)
            camera.contrast = contrast
        else: 
            self.contrast_input.setText('0')
    
    # AWB Mode Adjustment Methdods
    def awb_modeCombo_selected(self):
        global awb_mode
        awb_mode = self.awb_mode_combo.currentText()
        camera.awb_mode = awb_mode


    # AWB Gains Adjustment Methods
    def awb_gainsSlider_changed(self):
        global awb_gains
        awb_gainsTemp = int(self.awb_gains_slider.value()) 
        awb_gains = round(float(awb_gainsTemp / 1000),2)
        self.awb_gains_input.setText(str(awb_gains))
        camera.awb_gains = awb_gains

    # def awb_gainsInput_changed(self):
    #     global awb_gains
    #     if self.awb_gains_input.text():
    #         awb_gains = (float(self.awb_gains_input.text()) / 1000.000)
    #         self.awb_gains_slider.setValue(awb_gains)
    #         camera.awb_gains = awb_gains
    #     else: 
    #         self.awb_gains_input.setText('0')

    # ISO Adjustment Methods    
    def isoSlider_changed(self):
        global iso 
        iso = int(self.iso_slider.value()) 
        self.iso_input.setText(str(iso))
        camera.iso = iso

    def isoInput_changed(self):
        global iso
        if self.iso_input.text():
            iso = int(self.iso_input.text())
            self.iso_slider.setValue(iso)
        else: 
            self.iso_input.setText('0')

    # Framerate Adjustment Methods
    def framerateCombo_selected(self):
        changeFramerate(self.framerate_combo.currentText())
        global framerate
        framerate = self.framerate_combo.currentText()

    # Shutter Speed Adjustment Methods
    def shutter_speedCombo_selected(self):
        changeShutterSpeed(self.shutter_speed_combo.currentText())
        global shutter_speed
        shutter_speed = self.shutter_speed_combo.currentText()

    # Start Preview Button
    def startPreview_btnClicked(self):
        camPreviewWindowed()

    # Stop Preview Button
    def stopPreview_btnClicked(self):
        camStopPreview()

    # Test Shot Button
    def testShot_btnClicked(self):
        testShot()
        
    # Project Name Field
    def projectName_fieldChanged(self):
        global projectName
        projectName = self.project_name_input.text()

    # Camera Movement Adjustment Methods
    def cameraMovementSlider_changed(self):
        global cameraMovement
        cameraMovement = int(self.camera_movement_slider.value())
        self.camera_movement_input.setText(str(cameraMovement))

    def cameraMovementInput_changed(self):
        global cameraMovement
        cameraMovement = int(self.camera_movement_input.text()) 
        self.camera_movement_slider.setValue(cameraMovement)

    # Camera Reverse Button            
    def cameraReverse_btnClicked(self):
        reverse()

    # Camera Forward Button
    def cameraForward_btnClicked(self):
        forward()

    # Set Home Button
    def setHome_btnClicked(self):
        setHome()

    # Go Home Button
    def goHome_btnClicked(self):
        goHome()

    # Location Readout Value
    def locationValue_update(self):
        self.location_value_lbl.setText("0")

    # Shots in Stack Adjustment Methods
    def num_shotsSlider_changed(self):
        global numberShots
        numberShots = self.num_shots_slider.value()
        self.num_shots_input.setText(str(numberShots))
 
    def num_shotsInput_changed(self):
        global numberShots
        numberShots = int(self.num_shots_input.text())
        self.num_shots_slider.setValue(numberShots)

    # Single Shot Button
    def singleShot_btnClicked(self):
        shoot()

    # Shoot Stack Button
    def shootStack_btnClicked(self):
        runStackRoutine()

    # Dolly Movement Adjustment Methods
    def dollyMovementSlider_changed(self):
        global dollyMovement
        global arcLength
        global numberStacks
        dollyMovement = self.dolly_movement_slider.value()
        self.dolly_movement_input.setText(str(dollyMovement))
        numberStacks = arcLength // dollyMovement

    def dollyMovementInput_changed(self):
        global dollyMovement
        global arcLength
        global numberStacks
        dollyMovement = int(self.dolly_movement_input.text())
        self.dolly_movement_slider.setValue(dollyMovement)
        numberStacks = arcLength // dollyMovement
    
    # Arc Length Adjustment Methods
    def arcLengthSlider_changed(self):
        global arcLength
        global dollyMovement
        global numberStacks
        arcLength = self.arc_length_slider.value()
        self.arc_length_input.setText(str(arcLength))
        numberStacks = arcLength // dollyMovement        

    def arcLengthInput_changed(self):
        global arcLength
        global dollyMovement
        global numberStacks
        arcLength = int(self.arc_length_input.text())
        self.arc_length_slider.setValue(arcLength)
        numberStacks = arcLength // dollyMovement

    # Direction ComboBox
    def directionCombo_selected(self):
        global direction
        direction = self.direction_combo.currentText()

    # Export Settings Button()
    def exportSettings_btnClicked(self):
        exportSettings()
        #loadDefaultSettings()

    def runFullRoutine_btnClicked(self):
        runFullRoutine()
    




if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    #loadDefaultSettings()
    sys.exit(app.exec_())
