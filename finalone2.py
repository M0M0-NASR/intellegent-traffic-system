
import queue
from math import ceil
import sys
import threading
import cv2
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont , QImage , QPixmap
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QLineEdit, QFrame, QApplication
from ultralytics import YOLO

class Gui(QWidget):

    def __init__(self):

        super().__init__()

        # save Snapshots here
        self.frames = []

        # init Componants
        self.initComponets()

    def initComponets(self):

        #types of veichles
        self.createVeichles()

        # create and Config Big Window
        self.createWindow()

        # create Vidoes frame
        self.createVidoeFrame()

        # create Control frame
        self.createControlFrame()

        # check Traffic lights and  connect them
        self.createTraffics()

        # create Veichles components
        self.createVeichles()

    def createVeichles(self):

        # create type of car that system can detect
        self.veichlesTypes = []
        for type in Veichle.types:
            self.veichlesTypes.append(Veichle(type, 5))

    def createTraffics(self):

        # create 4 traffic for each road
        self.traffics =[]

        for i in range(4):
            self.traffics.append(TrafficLight(self.controlFrame , i+1))

            # init traffic timer
            self.timer = QTimer(self.traffics[i].frame)
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.update_timer)

    def connectCameras(self):

        # connect camera with system and show it in video label
        self.cameras = []

        # because we didnt have real camera we use videos insted
        videoNames = ["2.mp4", "3.mp4", "4.mp4", "5.mp4"]

        for i in range(4):
            self.cameras.append(Camera(videoNames[i], self.videoLabels[i], str(i), Road(str(i))))

    def startStream(self):
        # here we start show stream in system
        try:
            self.connectCameras()
            for camera in self.cameras:
                camera.start()

        except Exception as ex:
            e = ex.__traceback__
            print(e.tb_lineno)

    def predict(self):
        self.t  = 1


        # this run at first for one time then system start with itself
        try:
            # take four frames and add it in frames list
            for camera in self.cameras:
                self.frames.append(camera.getFrame())
                camera.pause = True
            # create model and pass frames list
            self.model = Model()
            thr = threading.Thread(target=self.model.detec_thread , args=([self.frames]))
            thr.start()

            # after thread finish it returned list of data boxes
            detections = self.model.my_queue.get(True)

            # after that count veichles by Camera method that save result in road.veichles
            # then add each road with its count to road_veichles like {road: count}
            road_veichles = {}
            i = 0
            for camera in self.cameras:
                camera.countVeichles(detections[i])
                road_veichles.setdefault(camera.road.roadID, camera.road.getVeichles())
                i += 1

            # then pass road_veichles to calcGreenTime method run traffic with time
            road_and_time = TrafficLight.calcGreenTime(road_veichles, self.veichlesTypes)

            # here clear frames list to next frames
            self.frames.clear()

            # init timer traffic with init road and time
            self.start_timer(road_and_time)

        except Exception as ex:
            e = ex.__traceback__
            print(e.tb_lineno)

    def start_timer(self, road_and_time):

        # here we start time to specefied road
        try:
            # road_and_time is dict has two best road to open like {0:12,1:43}

            # we extract last key and value
            self.openroads = road_and_time
            self.roadID , self.time = road_and_time.popitem()

            # then make it road open to serve in piroi
            self.cameras[int(self.roadID)].road.isOpen = True
            self.cameras[int(self.roadID)].pause = False
            self.traffics[int(self.roadID)].roadLabel.setText("Road #" + str(int(self.roadID) + 1) +" OPENED")
            self.traffics[int(self.roadID)].setgreenTime(self.time*4)

            self.timer.start()

        except Exception as ex:
            e = ex.__traceback__
            print(e.tb_lineno)

    def update_timer(self):


        try:
            # here update time each second and decreament time
            self.traffics[int(self.roadID)].greenTime -= 1
            self.traffics[int(self.roadID)].remineTimeLabel.setText(str(self.traffics[int(self.roadID)].greenTime))

            # this run if we second 30
            if self.traffics[int(self.roadID)].greenTime == 30:

                self.frames.clear()

                # here check if road_and_time is empty we should run model to add new Two road
                # the road that open we mask it to false
                if (len(self.openroads) == 0):

                    print("now is zero")
                    # we take frames for camera that is false ==> that road not open yet
                    for camera in self.cameras:
                        if camera.road.isOpen == False:
                            self.frames.append(camera.getFrame())
                            camera.road.isOpen = True
                        else:
                            camera.road.isOpen = False

                    thr = threading.Thread(target=self.model.detec_thread , args=([self.frames]))
                    thr.start()

            # this run if we second 30
            if self.traffics[int(self.roadID)].greenTime == 0:
                self.cameras[int(self.roadID)].pause = True
                self.traffics[int(self.roadID)].roadLabel.setText("Road #" + str(int(self.roadID) + 1) + " CLOSED")
                # we complete work by the result and pass it to Camera method then to CalcGreen Time
                if len(self.openroads) == 0:
                    detections = self.model.my_queue.get(False)

                    road_veichles = {}

                    # we update count who is True
                    i = 0
                    for camera in self.cameras:
                        print(camera.road.roadID)
                        print(camera.road.isOpen)
                        if camera.road.isOpen == True:

                            camera.countVeichles(detections[i])
                            road_veichles.setdefault(camera.road.roadID, camera.road.getVeichles())
                            i += 1
                    road_and_time = TrafficLight.calcGreenTime(road_veichles, self.veichlesTypes)
                    self.start_timer(road_and_time)

                else:
                    self.start_timer(self.openroads)
                self.t += 1
                print("tries = " + str(self.t))
            print(self.traffics[int(self.roadID)].greenTime)

        except Exception as ex:
            e = ex.__traceback__
            print(e.tb_lineno)

    def createWindow(self):

        #set main window configs
        self.setWindowTitle("GP Traffic System")
        self.window = QWidget(self)
        self.window.resize(1300, 700 )
        self.window.setStyleSheet("background-color:gray")

    def createVidoeFrame(self):

        ######### create Vidoes frame #########
        self.videosFrame = QFrame(self.window)
        self.videosFrame.setStyleSheet("background-color:white")
        self.videosFrame.resize(900, 700)

        self.videoLabels = []



        # create 4 labels to show videos
        # video label 1
        self.vidLabel1 = QLabel(self.videosFrame)
        self.vidLabel1.resize(440, 340)
        self.vidLabel1.setStyleSheet("background-color:black")

        # video label 2
        self.vidLabel2 = QLabel(self.videosFrame)
        self.vidLabel2.resize(440, 340)
        self.vidLabel2.setStyleSheet("background-color:black")
        self.vidLabel2.move(450, 0)

        # video label 3
        self.vidLabel3 = QLabel(self.videosFrame)
        self.vidLabel3.resize(440, 340)
        self.vidLabel3.setStyleSheet("background-color:black")
        self.vidLabel3.move(0, 350)

        # video label 4
        self.vidLabel4 = QLabel(self.videosFrame)
        self.vidLabel4.resize(440, 340)
        self.vidLabel4.setStyleSheet("background-color:black")
        self.vidLabel4.move(450, 350)

        self.videoLabels.append(self.vidLabel1)

        self.videoLabels.append(self.vidLabel2)
        self.videoLabels.append(self.vidLabel3)
        self.videoLabels.append(self.vidLabel4)

    def createControlFrame(self):
        ########## create Control farme #############
        self.controlFrame = QFrame(self.window)
        self.controlFrame.setStyleSheet("background-color: grey")
        self.controlFrame.resize(400, 700)
        self.controlFrame.move(900, 0)

        # create fonts here
        labelFont = QFont("Arial", 18, 700)
        inputFont = QFont("Arial", 14)
        btnFont = QFont("Arial", 12)

        # create Max label and input
        # label here
        self.maxlabel = QLabel("Max Time:", self.controlFrame)
        self.maxlabel.setFont(labelFont)
        self.maxlabel.setStyleSheet("font-weight:bold")
        self.maxlabel.move(10, 15)

        # input here
        self.maxInput = QLineEdit(self.controlFrame)
        self.maxInput.move(130, 15)
        self.maxInput.resize(100, 30)
        self.maxInput.setFont(inputFont)
        self.maxInput.setStyleSheet("background-color:white")

        # create Max label and input
        # label here
        self.minlabel = QLabel("Min Time:", self.controlFrame)
        self.minlabel.setFont(labelFont)
        self.minlabel.setStyleSheet("font-weight:bold")
        self.minlabel.move(10, 50)

        # input here
        self.minInput = QLineEdit(self.controlFrame)
        self.minInput.move(130, 50)
        self.minInput.resize(100, 30)
        self.minInput.setFont(inputFont)
        self.minInput.setStyleSheet("background-color:white")

        # create button to start Project
        self.startBtn = QPushButton("Start", self.controlFrame)
        self.startBtn.move(10, 90)
        self.startBtn.resize(190, 30)
        self.startBtn.setFont(btnFont)
        self.startBtn.setStyleSheet("background-color:white")
        self.startBtn.clicked.connect(self.startStream)

        # create button to stop Project
        self.stopBtn = QPushButton("Predict", self.controlFrame)
        self.stopBtn.move(200, 90)
        self.stopBtn.resize(190, 30)
        self.stopBtn.setFont(btnFont)
        self.stopBtn.setStyleSheet("background-color:white")
        self.stopBtn.clicked.connect(self.predict)

class Road:

    def __init__(self , roadID):
        self.isOpen = False
        self.roadID = roadID
        self.veichles = {}   # Contain types and number of classes

    def getStatus(self):
        return self.isOpen

    def setStatus(self, status):
        self.isOpen = status

    def getRoadID(self):
        return self.roadID

    def setStatus(self, roadID):
        self.roadID = roadID

    def getVeichles(self):
        return self.veichles

class TrafficLight():

    j = 140
    def __init__(self, window, ID):

        self.ID = ID
        self.redTime = 0;
        self.greenTime = 0;
        self.yellowTime = 0;
        self.design(window, TrafficLight.j+10)
        TrafficLight.j +=140
        # print(TrafficLight.j)

    def setRedTime(self, redTime):
        self.redTime = redTime

    def setgreenTime(self, greenTime):
        self.greenTime = greenTime

    def setYellowTime(self, yellowTime):
        self.yellowTime = yellowTime

    def getRedTime(self):
        return self.redTime

    def getGreenTime(self):
        return self.greenTime

    def getYellowTime(self):
        return self.yellowTime

    # code traffic Design
    def design(self, window, j):

        # white frame
        self.frame = QFrame(window)
        self.frame.resize(380, 120)
        self.frame.move(10, j) #10 , 140
        self.frame.setStyleSheet("background-color:white; border-radius:5%")
        self.roadLabel = QLabel("Road #"+str(self.ID)+ " CLOSED", self.frame)
        self.roadLabel.setFont((QFont("Arail", 20)))
        self.roadLabel.move(10, 5)

        # the black container
        self.container = QFrame(self.frame)
        self.container.resize(160, 60)
        self.container.move(10, 50)
        self.container.setStyleSheet("background-color:black;border-radius:10%")

        # red light
        self.redlabel = QLabel(self.container)
        self.redlabel.resize(40 , 40)
        self.redlabel.setStyleSheet("border-radius:20%; background-color:red")
        self.redlabel.move(110,10)

        # green light
        self.greenlabel = QLabel(self.container)
        self.greenlabel.resize(40, 40)
        self.greenlabel.setStyleSheet("border-radius:20%; background-color:green")
        self.greenlabel.move(10, 10)

        # yellow light
        self.yellowlabel = QLabel(self.container)
        self.yellowlabel.resize(40, 40)
        self.yellowlabel.setStyleSheet("border-radius:20%; background-color:yellow")
        self.yellowlabel.move(60, 10)

        # remining time label
        self.remineTimeLabel = QLabel(self.frame)
        self.remineTimeLabel.resize(30,30)
        self.remineTimeLabel.setFont((QFont("Arail", 20)))
        self.remineTimeLabel.move(200, 60)  # plus 60 to Y for next light
        self.remineTimeLabel.setStyleSheet("color:green; background-color:black")

    @classmethod
    def calcGreenTime(cls,road_veichles , veichles_types):

        road_times = {}
        for road, number in road_veichles.items():
            # road_times.append()
            road_times.setdefault(road, int(Helper.GST(number, 4, veichles_types)))
        # print(road_times)
        # print("tmaaam1")
        return Helper.piror(road_times , road_veichles)

class Model:

    def __init__(self):

        self.weights = "best.pt"
        self.model = YOLO(self.weights)
        self.my_queue = queue.Queue()

    def detect(self, frames):
        detections = []

        try:
                #cv2.resize(frames.pop(), (640, 640))
                result = self.model.predict(frames, conf=.5, iou=.4)
                res = result

                for i in res:
                    detections.append(i.boxes.cpu().numpy())

        except Exception as er:
            print(er)

        return detections

    def detec_thread(self , frames):
        self.my_queue.put(self.detect(frames))

class Veichle:

    types = {"car": 5, "truck": 5, "bike": 5, "motorbike": 5, "bus": 5, "ambluance": 5, "firecar": 5}

    def __init__(self, type, avr_speed):
        self.type = type
        self.avr_speed = avr_speed

    def setType(self , type):
        self.type = type

    def getType(self):
        return self.type

    def setSpeed(self, avr_speed):
        self.avr_speed = avr_speed

    def getspeed(self):
        return self.avr_speed

class Camera(Gui):


    def __init__(self, video_src , qlabel, ID , road):
        super().__init__()
        self.videolabel = qlabel
        self.cap = cv2.VideoCapture(video_src)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.cameraID = ID
        self.road = road
        self.pause = False
    def start(self):
        self.timer.start(50)  # 30 fps

    def stop(self):
        self.timer.stop()

    def getFrame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.resize(frame, (440 , 340))
            return frame
        self.cap.release()

    # Abstract method To loop and Update frames
    def update_frame(self):
        if not self.pause:
            ret, frame = self.cap.read()
            self.frames = [frame]
            if ret:

                # Convert the frame to a QImage and display it in the label
                frame = cv2.resize(frame, (440 , 340))
                image = QImage(frame, frame.shape[1], frame.shape[0], QImage.Format_BGR888)
                pixmap = QPixmap.fromImage(image)
                self.videolabel.setPixmap(pixmap)
                self.frames =[frame]
                self.frames.append(frame)
            if not self.cap.isOpened():
                self.start()

    # function must return Dict type
    def countVeichles(self, detections):

        # This for save count
        classes = { 0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0 }
        for i in detections.data:
            if int(i[5]) == 0:
                classes[0] += 1
            if int(i[5]) == 1:
                classes[1] += 1
            if int(i[5]) == 2:
                classes[2] += 1
            if int(i[5]) == 3:
                classes[3] += 1
            if int(i[5]) == 4:
                classes[4] += 1
            if int(i[5]) == 5:
                classes[5] += 1
            if int(i[5]) == 6:
                classes[6] += 1
        self.road.veichles = classes

################ This classs for Helper Func like count And Time Calc
class Helper:

    # Return Greean Time
    @staticmethod
    def GST( detections, noLanes, types):
        sum = 0
        i = 0
        for type in types:
            sum += detections[i] * type.avr_speed
            i += 1

        return ceil(float(sum) / float(noLanes))
    # Piroir part is here
    @staticmethod
    def piror(road_times, road_veichles):
        # print(road_times)
        try:
            road_and_time = {}

            max = 0
            index = None
            pervMax = 0
            pervIndex = None

            for road, veichles in road_veichles.items():
                if (list(veichles.values())[5] > 0 or list(veichles.values())[6] > 0):
                    pass
                    road_and_time.setdefault(road, list(road_times.values())[int(road)])
                    road_times.pop(road)
            print("1")
            print(road_and_time)

            if(len(road_and_time) < 2):
                # print("here")
                # print(len(road_and_time))
                for road, time in road_times.items():
                    if( time >= max):
                        pervMax = max
                        pervIndex = index
                        max = time
                        index = road

                if( len(road_and_time) == 0):
                    road_and_time.setdefault(pervIndex, pervMax)
                    road_and_time.setdefault(index, max)

                if(len(road_and_time)== 1):
                    road, time = road_and_time.popitem()

                    road_and_time.setdefault(index , max)
                    road_and_time.setdefault(road, time)
            print("2")
            print(road_and_time)

            r, i = 0,0;

            for road , time in road_and_time.items():


                if (time < 7):
                    road_and_time[road] = 9
                if ( road == None):
                    r , i =  road_times.popitem()
                    road_and_time.pop(road)
                    road_and_time.setdefault(r,i)
                    print("road and times ==")
                    print(road_times)
                    print("ues")
                    break

            print("3")

            print(road_and_time)
            print(road_times)
            return road_and_time

        except Exception as e:

            print("error")
            print(e)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Gui()
    window.move(30,10)
    window.show()
    sys.exit(app.exec_())

    # {'0': 9, '1': 2, '2': 8, '3': 10}
