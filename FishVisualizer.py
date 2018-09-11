import Tkinter
import random
import os
import csv
#from datetime import datetime
import datetime
import tkFileDialog
import ntpath
import numpy as np
from PIL import ImageTk,Image  
import tkMessageBox
import pickle
import time

def normalize_points(points):
    points_a = np.array(points, dtype=np.float32)
    points_a -= np.amin(points_a, 0)
    points_a *= 10 / np.amax(points_a, 0)
    return points_a


def jitter_points(points, scale):
    ret_points = []
    points = np.array(points)[:, 0:2].astype(float)
    for p in points:
        noise = np.random.normal(scale=scale, size=p.size)
        ret_points.append(np.absolute(noise + p))
    return ret_points


def write_points(points, filename, tag = "1111.111"):
    f = open(filename, "w")
    f.write(
        "\"TagCode\",\"Date\",\"Time\",\"Easting\",\"Northing\",\"DateTime\",\"Period\",\"Period2\",\"Species\",\"Trial\""
    )
    for s, d in enumerate(points):
        f.write(
            tag + (",NA,NA,{0:.2f},{1:.2f}," + str(d[2]) +",NA,NA,Synthetic Data,NA\n").format(d[0], d[1]))

def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

def read_and_sort_csv(filename):
    try:
        fish_pos = {}
        tag_col = 0
        east_col = 3
        north_col = 4
        date_col = 5
        time_formatMilli = '%Y-%m-%d %H:%M:%S.%f'
        time_format = '%Y-%m-%d %H:%M:%S'
        with open(filename) as f:
            f_data = csv.reader(f, delimiter=',')
            f_data.next()
            #f_data_sorted = sorted(f_data,key=lambda row: datetime.strptime(row[date_col], time_format))
            f_data_sorted = f_data
            f.seek(0)
            f_data.next()
            #fish_pos = {}

            row_count = 0
            for i, entry in enumerate(f_data_sorted):
                try:
                    row_count += 1
                    if len(entry) < 1:
                        return None
                    tag = entry[tag_col]
                    east = float(entry[east_col])
                    north = float(entry[north_col])
                    try:
                        time = datetime.datetime.strptime(entry[date_col], time_formatMilli)
                    except:
                        time = datetime.datetime.strptime(entry[date_col], time_format)
                    species = entry[8]
                    if tag + " (" + ntpath.basename(filename) + ")" not in fish_pos:
                        fish_pos[tag + " (" + ntpath.basename(filename) + ")"] = [[east, north, species, time]]
                    else:
                        fish_pos[tag + " (" + ntpath.basename(filename) + ")"].append([east, north, species, time])
                except:
                    return None
            if row_count < 2: 
                return None
        return fish_pos
    except:
        return None

def corner_cut(points, iterations): 
    points = np.array(points)[:, 0:2].astype(float)

    smooth_points = points

    for _ in range(iterations):
        L = smooth_points.repeat(2, axis=0)
        R = np.empty_like(L)
        R[0] = L[0]
        R[2::2] = L[1:-1:2]
        R[1:-1:2] = L[2::2]
        R[-1] = L[-1]
        smooth_points = L * 0.75 + R * 0.25
    return smooth_points


def calc_next_kalman(x, P, measurement):
    R = 0.01**2
    motion = np.matrix('0. 0. 0. 0.').T
    Q = np.matrix(np.eye(4))
    F = np.matrix('''
    1. 0. 1. 0.;
    0. 1. 0. 1.;
    0. 0. 1. 0.;
    0. 0. 0. 1.
    ''')
    H = np.matrix('''
    1. 0. 0. 0.;
    0. 1. 0. 0.''')

    y = np.matrix(measurement).T - H * x
    S = H * P * H.T + R  # residual convariance
    K = P * H.T * S.I  # Kalman gain
    x = x + K * y
    I = np.matrix(np.eye(F.shape[0]))  # identity matrix
    P = (I - K * H) * P

    # PREDICT x, P based on motion
    x = F * x + motion
    P = F * P * F.T + Q

    return x, P

def kalman_filter(points):
    print "Running Kalman Filter"
    points = np.array(points)[:, 0:2].astype(float)
    x = np.matrix('0. 0. 0. 0.').T
    P = np.matrix(np.eye(4)) * 1000  # initial uncertainty
    result = []
    for meas in points:
        x, P = calc_next_kalman(x, P, meas)
        result.append((x[:2]).tolist())
    print "Done"
    return np.squeeze(np.array(result).astype(int))

class LoadingScreen(Tkinter.Toplevel):
    def __init__(self, parent, message):
        Tkinter.Toplevel.__init__(self, parent)
        self.overrideredirect(1)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        y = parent.winfo_y()
        x = parent.winfo_x()
        height = parent.winfo_height()
        width = parent.winfo_width()
        self.geometry("550x150+%d+%d" % (x + int(width/2) - 550/2, y + int(height/2) - 150/2))
        self.lift()
        self.title("Loading")
        
        Tkinter.Label(self, text = message, font=("Helvetica Neue Bold", 18)).pack(padx=5, pady=20, side=Tkinter.TOP)
        self.update()
    def updateWheel(self):

        self.sequenceIndex += 1
        self.sequenceIndex = self.sequenceIndex % 4
        self.wheelState.set(self.sequence[self.sequenceIndex])
        self.after(1, self.updateWheel)

class ShowTextScreen(Tkinter.Toplevel):
    def __init__(self, parent, text):
        Tkinter.Toplevel.__init__(self, parent)
        self.overrideredirect(0)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        y = parent.winfo_y()
        x = parent.winfo_x()
        height = parent.winfo_height()
        width = parent.winfo_width()
        self.geometry("650x350+%d+%d" % (x + int(width/2) - 550/2, y + int(height/2) - 150/2))
        self.lift()
        self.title("Help")
        
        # create a Frame for the Text and Scrollbar
        txt_frm = Tkinter.Frame(self, width=650, height=300)
        txt_frm.pack(fill="both", expand=True)
        # ensure a consistent GUI size
        txt_frm.grid_propagate(False)
        # implement stretchability
        txt_frm.grid_rowconfigure(0, weight=1)
        txt_frm.grid_columnconfigure(0, weight=1)

        # create a Text widget
        self.txt = Tkinter.Text(txt_frm, borderwidth=3, relief="sunken")
        self.txt.config(font=("consolas", 12), undo=True, wrap='word')
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.txt.insert(Tkinter.INSERT, text , "a")
        self.txt.config(state="disabled")

        # create a Scrollbar and associate it with txt
        scrollb = Tkinter.Scrollbar(txt_frm, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set

        
        Tkinter.Button(self, text = "close", font=("Helvetica Neue Bold", 12), command = self.closePress).pack(padx=5, pady=5, side=Tkinter.TOP)

    def closePress(self):
        self.destroy()

class HelpScreen(Tkinter.Toplevel):
    def __init__(self, parent):
        Tkinter.Toplevel.__init__(self, parent)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        y = parent.winfo_y()
        x = parent.winfo_x()
        height = parent.winfo_height()
        width = parent.winfo_width()
        self.geometry("650x350+%d+%d" % (x + int(width/2) - 550/2, y + int(height/2) - 150/2))
        self.lift()
        self.title("Instructions")

        # create a Frame for the Text and Scrollbar
        txt_frm = Tkinter.Frame(self, width=650, height=300)
        txt_frm.pack(fill="both", expand=True)
        # ensure a consistent GUI size
        txt_frm.grid_propagate(False)
        # implement stretchability
        txt_frm.grid_rowconfigure(0, weight=1)
        txt_frm.grid_columnconfigure(0, weight=1)

        # create a Text widget
        self.txt = Tkinter.Text(txt_frm, borderwidth=3, relief="sunken")
        self.txt.config(font=("consolas", 12), undo=True, wrap='word')
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.txt.insert(Tkinter.INSERT, "Description:\nThis program plots fish locations at any given time. A line is drawn between data points to show where the fish has been. To get started, load in a fish data file. See the section below.\n\nLoading Data:\nClick \"File\" -> \"Open Fish Data File\" and select a .csv file to load. Large files may take a while to load (trial1data.cvs takes abot 30 seconds on my machine).\n\nLoading A Background Image:\nYou can load a jpg or png image as the background via \"File -> Load Background Image\" When you load a new background image, any existing loaded fish data will automatically be rescaled to the new background image size. See the \"Note About Scaling\" section for details on how the scaling works. If there is a file named \"pond.jpg\" in the same folder as this program then pond.jpg will be loaded as the default background when the program launches.\n\nNote About Scaling:\nAt this point all fish data is assumed to be taken from the left tank and that the background image is of two tanks side by side. This means all real fish data will be scaled linearly such that the furthest east the fish go is about the middle of the Fish Path drawing area. The exception to this is Synthetic data that is recorded with this program. Synthetic data will not be scaled at all, so I recommend only using synthetic data with the same background image that it was recorded with for now. The program identifies synthetic data as any fish who's species is \"Synthetic Data\"\n\nRecording Data:\nPress \"Recording\" -> \"Start Recording Data\". Click and hold the left mouse button while moving mouse over the fish draw area to record. When finished pres \"Recording\" -> \"Finish Recording Data\". You will be prompted to save the recording, then prompted again if you want to open it at that time.\n\nSaving/Restoring State\n\"File\" -> Save State\" will save the current background, fish data, time, and filter settings. You can only save state after loading a fish file or loading a recording. Saving state while recording isn't supported. Youc an restore state anytime via \"File\" -> \"Restore State\" will restore your state from save state file(\".fvs\").\n\nApplying Filters and Distortions:\nFor each fish path (represented by a different color box on the far right side of the main window) you can apply a filter, and/or a distortion, or neither. Distortions are applied before filters are applied. \n\nDescription of Filters:\nAveraging - Each point is replaced by the average of itself, the two points before it, and the two points after it.\nKalman Filter - The Kalman filter attempts to reconcile the differences between the predicted location of the fish (based on a physical model of what is possible), and the measured location of the fish using a probabalistic model.\nCorner Cut - Every point is replaced by two points. The two new points are placed so as to minimize the sharpness of corners.\n\nDiscription of Distortions:\nJitter distortion- Randomly adds a value between 0 and 5 in X and Y to each point. "  , "a")
        self.txt.config(state="disabled")

        # create a Scrollbar and associate it with txt
        scrollb = Tkinter.Scrollbar(txt_frm, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set

        
        Tkinter.Button(self, text = "close", font=("Helvetica Neue Bold", 12), command = self.closePress).pack(padx=5, pady=5, side=Tkinter.TOP)

    def closePress(self):
        self.destroy()

class AboutScreen(Tkinter.Toplevel):
    def __init__(self, parent):
        Tkinter.Toplevel.__init__(self, parent)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        y = parent.winfo_y()
        x = parent.winfo_x()
        height = parent.winfo_height()
        width = parent.winfo_width()
        self.geometry("650x350+%d+%d" % (x + int(width/2) - 550/2, y + int(height/2) - 150/2))
        self.lift()
        self.title("About")

        # create a Frame for the Text and Scrollbar
        txt_frm = Tkinter.Frame(self, width=650, height=300)
        txt_frm.pack(fill="both", expand=True)
        # ensure a consistent GUI size
        txt_frm.grid_propagate(False)
        # implement stretchability
        txt_frm.grid_rowconfigure(0, weight=1)
        txt_frm.grid_columnconfigure(0, weight=1)

        # create a Text widget
        self.txt = Tkinter.Text(txt_frm, borderwidth=3, relief="sunken")
        self.txt.config(font=("consolas", 12), undo=True, wrap='word')
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.txt.insert(Tkinter.INSERT, "Fish Visualizer Beta 1.0\n\nCreated by Brigham Young University under the direction of Dr. DJ Lee for the United States Geological Survey.\n\nThis is an beta version so new features are being added regularly.\n\nReport bugs to mheydorn@byu.edu", "a")
        self.txt.config(state="disabled")

        # create a Scrollbar and associate it with txt
        scrollb = Tkinter.Scrollbar(txt_frm, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set
        
        Tkinter.Button(self, text = "close", font=("Helvetica Neue Bold", 12), command = self.closePress).pack(padx=5, pady=5, side=Tkinter.TOP)

    def closePress(self):
        self.destroy()

class RecordingScreen(Tkinter.Toplevel):
    def __init__(self, parent, mainClass):
        Tkinter.Toplevel.__init__(self, parent)
        self.overrideredirect(1)
        self.mainClass = mainClass
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        y = parent.winfo_y()
        x = parent.winfo_x()
        height = parent.winfo_height()
        width = parent.winfo_width()
        self.geometry("350x150+%d+%d" % (x + int(width/2) - 550/2, y + int(height/2) - 150/2))
        self.lift()
        self.title("Recording Options")
        self.recordingIntervalVar = Tkinter.StringVar(self)
        self.recordingIntervalVar.set("1")
        Frame1 = Tkinter.Frame(self, borderwidth = 1)
        Tkinter.Label(Frame1, text = "Recording Speed", font=("Helvetica Neue Bold", 12)).pack(padx=5, pady=5, side=Tkinter.LEFT)
        Tkinter.Spinbox(Frame1, from_=1, to=1000, width = 5, textvariable = self.recordingIntervalVar).pack(padx=5,side=Tkinter.RIGHT)
        Frame1.pack(padx=10, pady=5, side=Tkinter.TOP)

        self.tagNameVar = Tkinter.StringVar(self)
        self.tagNameVar.set("1111.1111")

        Frame1 = Tkinter.Frame(self, borderwidth = 1)
        Tkinter.Label(Frame1, text = "Tag Name", font=("Helvetica Neue Bold", 12)).pack(padx=5, pady=5, side=Tkinter.LEFT)
        Tkinter.Entry(Frame1, width = 20, textvariable = self.tagNameVar).pack(padx=5,side=Tkinter.RIGHT)
        Frame1.pack(padx=10, pady=0, side=Tkinter.TOP)

        miniFrame = Tkinter.Frame(self)
        Tkinter.Button(miniFrame, text = "Start", font=("Helvetica Neue Bold", 12), command = self.startPress).pack(padx=5, pady=5, side=Tkinter.LEFT)
        Tkinter.Button(miniFrame, text = "Cancel", font=("Helvetica Neue Bold", 12), command = self.cancel).pack(padx=5, pady=5, side=Tkinter.LEFT)
        miniFrame.pack(padx=5, pady=0, side=Tkinter.TOP)
        self.update()

    def startPress(self):
        self.mainClass.recordInterval = int(self.recordingIntervalVar.get())
        self.mainClass.recordTagName = str(self.tagNameVar.get())
        self.mainClass.recording = True
        self.destroy()
    def cancel(self):
        self.mainClass.recording = False
        self.destroy()

class AskOpenNow(Tkinter.Toplevel):
    def __init__(self, parent, mainClass):
        Tkinter.Toplevel.__init__(self, parent)
        self.overrideredirect(1)
        self.mainClass = mainClass
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        y = parent.winfo_y()
        x = parent.winfo_x()
        height = parent.winfo_height()
        width = parent.winfo_width()
        self.geometry("250x75+%d+%d" % (x + int(width/2) - 250/2, y + int(height/2) - 75/2))
        self.lift()
        self.title("Open Now")
        Tkinter.Label(self, text = "Open Recording Now?", font=("Helvetica Neue Bold", 12)).pack(padx=5, pady=5, side=Tkinter.TOP)
        miniFrame = Tkinter.Frame(self)
        Tkinter.Button(miniFrame, text = "Yes", font=("Helvetica Neue Bold", 12), command = self.yes).pack(padx=5, pady=5, side=Tkinter.LEFT)
        Tkinter.Button(miniFrame, text = "No", font=("Helvetica Neue Bold", 12), command = self.no).pack(padx=5, pady=5, side=Tkinter.LEFT)
        miniFrame.pack(padx=5, pady=0, side=Tkinter.TOP)
        self.update()

    def yes(self):
        self.mainClass.saveNow = True
        self.destroy()
    def no(self):
        self.mainClass.saveNow = False
        self.destroy()

class PrompJitterScreen(Tkinter.Toplevel):
    def __init__(self, parent, mainClass):
        Tkinter.Toplevel.__init__(self, parent)
        self.overrideredirect(1)
        self.mainClass = mainClass
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        y = parent.winfo_y()
        x = parent.winfo_x()
        height = parent.winfo_height()
        width = parent.winfo_width()
        self.geometry("350x150+%d+%d" % (x + int(width/2) - 550/2, y + int(height/2) - 150/2))
        self.lift()
        self.title("Jitter Scale")
        self.jitterVar = Tkinter.StringVar(self)
        self.jitterVar.set("3.0")
        Frame1 = Tkinter.Frame(self, borderwidth = 1)
        Tkinter.Label(Frame1, text = "Jitter Spread Width (pixels)", font=("Helvetica Neue Bold", 12)).pack(padx=5, pady=20, side=Tkinter.LEFT)
        Tkinter.Spinbox(Frame1, from_=10, to=1000, width = 5, format = "%.2f" ,  textvariable = self.jitterVar).pack(padx=5,side=Tkinter.RIGHT)
        Frame1.pack(padx=5, pady=10, side=Tkinter.TOP)

        miniFrame = Tkinter.Frame(self)
        Tkinter.Button(miniFrame, text = "Ok", font=("Helvetica Neue Bold", 12), command = self.startPress).pack(padx=5, pady=5, side=Tkinter.LEFT)
        Tkinter.Button(miniFrame, text = "Cancel", font=("Helvetica Neue Bold", 12), command = self.cancel).pack(padx=5, pady=5, side=Tkinter.LEFT)
        #Tkinter.Button(miniFrame, text = "Help", font=("Helvetica Neue Bold", 12), command = self.showHelp).pack(padx=5, pady=5, side=Tkinter.LEFT)
        miniFrame.pack(padx=5, pady=0, side=Tkinter.TOP)
        self.update()

    def startPress(self):
        self.mainClass.jitterAmount = float(self.jitterVar.get())
        self.destroy()

    def cancel(self):
        self.mainClass.jitterAmount = -1
        self.destroy()

    def showHelp(self):
        showTextScreen = ShowTextScreen(self.mainClass.root, "This is the help page")
        showTextScreen.grab_set()

class App:
    
    def hello(self):
        print "hello!"

    def __init__(self, points):
        self.killUpdates = False
        self.restoring = False
        self.recordTagName = "1111.1111"
        self.beginTime = datetime.datetime(1900,1,1,1,1,1)
        self.endTime = datetime.datetime(1900,1,1,1,1,1)
        self.allTimes = []
        self.playing = False
        self.reversing = False
        self.currentTime = datetime.datetime(1970,1,1, 2,3,4)
        self.jitterAmount = 1.0
        self.mouseDown = False
        self.mousex = None
        self.mousey = None
        self.recordInterval = 1000
        self.recording = False
        self.fileLoaded = False
        self.pointsForEachFishBox = []
        for i in range(9):
            self.pointsForEachFishBox.append([[0,0], [0,0], [0, 0]])

        self.loaded = False 
        self.colors = ["red", "green", "blue",  "snow", "orange", "pale turquoise", "pink3", "purple2", "lime green"]

        self.fish = {}
        self.fishTagList = ['No Fish File Loaded']

        self.cachedKalmanFilters = {}
        self.cachedCornerFilters = {}

        self.root = Tkinter.Tk()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.call('wm', 'attributes', '.', '-alpha', True)
        self.root.title("Fish Movement Visualizer")
        bgColor = "#EDEDED"
        self.maxNumFish = 9
        self.root.configure(bg=bgColor)

        #File Menu
        menubar = Tkinter.Menu(self.root)

        # create a pulldown menu, and add it to the menu bar
        self.filemenu = Tkinter.Menu(menubar, tearoff=0)
        self.filemenu.add_command(label="Open Fish Data File", command=self.openFile)
        self.filemenu.add_command(label="Load Background Image", command=self.loadBackgroundImage)
        self.filemenu.add_command(label="Save State", command=self.saveState)
        self.filemenu.add_command(label="Restore State", command=self.restoreState)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=self.filemenu)

        self.recordMenu = Tkinter.Menu(menubar, tearoff=0)
        self.recordMenu.add_command(label="Start Recording Data", command=self.record)
        self.recordMenu.add_command(label="Finish Recording Data", command=self.finishRecording)
        #self.recordMenu.add_command(label="Add Jitter Noise", command=self.jitterRecording)
        self.recordMenu.entryconfig("Finish Recording Data", state="disabled")
        self.filemenu.entryconfig("Save State", state="disabled")
        #self.recordMenu.entryconfig("Add Jitter Noise", state="disabled")
        menubar.add_cascade(label="Record", menu=self.recordMenu)

        helpmenu = Tkinter.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Instructions", command=self.showHelpMenu)
        helpmenu.add_command(label="About", command=self.showAboutMenu)
        menubar.add_cascade(label="Help", menu=helpmenu)

        # display the menu
        self.root.config(menu=menubar)

        ############# Right Column ####################
        self.FrameRight = Tkinter.Frame(self.root, borderwidth = 1, bg=bgColor)
        #Tkinter.Label(self.FrameRight, text = "Options", font=("Helvetica Neue Bold", 14), bg = bgColor).pack(padx=5, pady=20, side=Tkinter.TOP)

        #Number of Paths to show at once
        miniFrame = Tkinter.Frame(self.FrameRight, borderwidth = 1, bg=bgColor)
        Tkinter.Label(miniFrame, text = "How Many Paths To Show", font=("Helvetica Neue Bold", 12), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        self.numFishToShow = Tkinter.StringVar(self.root)
        self.numFishToShow.set("3")
        Tkinter.Spinbox(miniFrame, from_=0, to=self.maxNumFish, width = 5, textvariable = self.numFishToShow).pack(padx=5,side=Tkinter.RIGHT)
        self.numFishToShow.trace(mode="w", callback=self.numFishChanged)
        miniFrame.pack(padx=5, pady=5, side=Tkinter.TOP)

        self.colorBoxFrame = Tkinter.Frame(self.FrameRight, borderwidth = 10, bg=bgColor)
        self.FishFrames = []
        for i in range(self.maxNumFish):
            self.FishFrames.append(Tkinter.Frame(self.colorBoxFrame, highlightbackground=self.colors[i], highlightcolor=self.colors[i], highlightthickness = 7,  borderwidth = 10, bg = bgColor))
        self.colorBoxFrame.pack(padx=5, pady=5, side=Tkinter.TOP)
        self.createFish()
        self.updateNumFish()

        self.FrameRight.grid(row = 0, column = 2, columnspan = 1, rowspan = 100, padx = 5, stick = "new")

        ###################  Center Column Start ##########################
        self.FrameCenter = Tkinter.Frame(self.root, borderwidth = 1, bg=bgColor)
        pady = 5
        #Canvas
        Tkinter.Label(self.FrameCenter, text = "Fish Paths", font=("Helvetica Neue Bold", 12), bg=bgColor).pack(padx=5, pady=5, side=Tkinter.TOP)
        self.Frame1 = Tkinter.Frame(self.FrameCenter, borderwidth = 1, relief = 'sunken')
        self.width = 400
        self.height = 400
        self.rawBackground = None
        self.plotArea = Tkinter.Canvas(self.Frame1, width=self.width, height=self.height)
        self.imgPhoto = None
        try:
            imgPil = Image.open("pond.jpg")
            self.rawBackground = imgPil
            self.width, self.height = imgPil.size
            self.imgPhoto = ImageTk.PhotoImage(imgPil)
            self.backgroundImage = self.plotArea.create_image(self.width/2,self.height/2, image=self.imgPhoto)
        except:
            pass

        self.plotArea.config(width=self.width, height=self.height)
        self.plotArea.pack()
        self.plotArea.configure(bg="black")
        self.Frame1.pack(padx=5, pady=pady, side=Tkinter.TOP)

        #Time display
        Frame1 = Tkinter.Frame(self.FrameCenter,  bg = bgColor,highlightbackground="gray", highlightcolor="gray", highlightthickness = 7)
        miniFrame = Tkinter.Frame(Frame1,bg=bgColor)
        Tkinter.Label(miniFrame, text = "Simulation Time (year-month-day hour:minute:second)", font=("Helvetica Neue Bold", 12), bg = bgColor).pack(pady=0, fill = Tkinter.X)

        self.currentTimeTK = Tkinter.StringVar(self.root)
        self.currentTimeTK.set(str(self.currentTime.strftime("%Y-%m-%d %H:%M:%S")))
        Tkinter.Label(miniFrame, textvariable = self.currentTimeTK, font=("Helvetica Neue Bold", 36), bg = bgColor).pack(pady=0, fill = Tkinter.X)

        miniFrame.pack(padx=5, pady=pady, side=Tkinter.TOP)
        Frame1.pack(padx=5, pady=pady, side=Tkinter.TOP)

        self.FrameCenter.grid(row = 0, column = 1, columnspan = 1, rowspan = 100, padx = 5, stick = "new")
        
        ###################  Left Column Start ##########################
        self.FrameLeft = Tkinter.Frame(self.root, borderwidth = 1, bg=bgColor)

        Tkinter.Label(self.FrameLeft, text = "", font=("Helvetica Neue Bold", 12), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.TOP)
        #Frame2 = Tkinter.Frame(self.FrameLeft, borderwidth = 0, bg = "gray")

        #Load Fish file menu
        
        self.fishDataFilename = Tkinter.StringVar(self.root)
        self.fishDataFilenameDisplay = Tkinter.StringVar(self.root)
        self.fishDataFilenameDisplay.set("Click Here to Load a Data File")

        #Buttons
        Frame1 = Tkinter.Frame(self.FrameLeft,  bg = bgColor,highlightbackground="gray", highlightcolor="gray", highlightthickness = 7)
        miniFrame = Tkinter.Frame(Frame1,bg=bgColor)
        Tkinter.Label(miniFrame, text = "Time Control", font=("Helvetica Neue Bold", 12), bg = bgColor).pack(pady=0, fill = Tkinter.X)
        Tkinter.Button(miniFrame, text = "Reverse", highlightbackground = bgColor, command = self.reverseButtonPress).pack(padx=5, pady=pady, side=Tkinter.LEFT)
        Tkinter.Button(miniFrame, text = "Pause", highlightbackground = bgColor, command = self.pauseButtonPress).pack(padx=5, pady=pady, side=Tkinter.LEFT)
        Tkinter.Button(miniFrame, text = "Play", highlightbackground = bgColor, command = self.playButtonPress).pack(padx=5, pady=pady, side=Tkinter.LEFT)
        miniFrame.pack(padx=5, pady=pady, side=Tkinter.TOP)
        Frame1.pack(padx=5, pady=pady, side=Tkinter.TOP)

        miniFrame = Tkinter.Frame(Frame1, bg=bgColor)
        Tkinter.Label(miniFrame, text = "PlayBack Speed:", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        self.timeMultiplierVar = Tkinter.StringVar(self.root)
        self.timeMultiplierVar.set(1)
        Tkinter.Spinbox(miniFrame, from_= 1, to = 1000, width = 5, textvariable = self.timeMultiplierVar).pack(padx=5,side=Tkinter.LEFT)
        Tkinter.Label(miniFrame, text = "x Real Speed", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        miniFrame.pack(fill = Tkinter.X)

        #Skip To time box
        Frame1 = Tkinter.Frame(self.FrameLeft, bg = bgColor, highlightbackground="gray", highlightcolor="gray", highlightthickness = 7)
        Tkinter.Label(Frame1, text = "Go to Time", font=("Helvetica Neue Bold", 12), bg = bgColor).pack(pady=0, fill = Tkinter.X)
        miniFrame = Tkinter.Frame(Frame1,  bg=bgColor)
#datetime.datetime(1970,1,1, 2,3,4)

        miniFrame2 = Tkinter.Frame(Frame1, bg=bgColor)
        Tkinter.Label(miniFrame2, text = "Year", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        self.gotoYear = Tkinter.StringVar(self.root)
        Tkinter.Spinbox(miniFrame2, from_=0, to=1000000, width = 5, textvariable = self.gotoYear).pack(padx=5, pady=0, side=Tkinter.LEFT)
        miniFrame2.pack(pady=5, fill = Tkinter.X)

        miniFrame2 = Tkinter.Frame(Frame1, bg=bgColor)
        Tkinter.Label(miniFrame2, text = "Month", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        self.gotoMonth = Tkinter.StringVar(self.root)
        Tkinter.Spinbox(miniFrame2, from_=0, to=1000000, width = 5, textvariable = self.gotoMonth).pack(padx=5, pady=0, side=Tkinter.LEFT)
        miniFrame2.pack(pady=5, fill = Tkinter.X)

        miniFrame2 = Tkinter.Frame(Frame1, bg=bgColor)
        Tkinter.Label(miniFrame2, text = "Day", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        self.gotoDay = Tkinter.StringVar(self.root)
        Tkinter.Spinbox(miniFrame2, from_=0, to=1000000, width = 5, textvariable = self.gotoDay).pack(padx=5, pady=0, side=Tkinter.LEFT)
        miniFrame2.pack(pady=5, fill = Tkinter.X)

        miniFrame2 = Tkinter.Frame(Frame1, bg=bgColor)
        Tkinter.Label(miniFrame2, text = "Hour", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        self.gotoHour = Tkinter.StringVar(self.root)
        Tkinter.Spinbox(miniFrame2, from_=0, to=1000000, width = 5, textvariable = self.gotoHour).pack(padx=5, pady=0, side=Tkinter.LEFT)
        miniFrame2.pack(pady=5, fill = Tkinter.X)

        miniFrame2 = Tkinter.Frame(Frame1, bg=bgColor)
        Tkinter.Label(miniFrame2, text = "Minute", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        self.gotoMinute = Tkinter.StringVar(self.root)
        Tkinter.Spinbox(miniFrame2, from_=0, to=1000000, width = 5, textvariable = self.gotoMinute).pack(padx=5, pady=0, side=Tkinter.LEFT)
        miniFrame2.pack(pady=5, fill = Tkinter.X)

        miniFrame2 = Tkinter.Frame(Frame1, bg=bgColor)
        Tkinter.Label(miniFrame2, text = "Second", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=5, side=Tkinter.LEFT)
        self.gotoSecond = Tkinter.StringVar(self.root)
        Tkinter.Spinbox(miniFrame2, from_=0, to=1000000, width = 5, textvariable = self.gotoSecond).pack(padx=5, pady=0, side=Tkinter.LEFT)
        miniFrame2.pack(pady=5, fill = Tkinter.X)

        #miniFrame2 = Tkinter.Frame(Frame1, bg=bgColor)
        Tkinter.Button(miniFrame, text = "Go", font=("Helvetica Neue Bold", 10), bg = bgColor, command = self.SkipTo).pack(padx=5, pady=0, side=Tkinter.TOP)

        Tkinter.Button(miniFrame, text = "Reset", font=("Helvetica Neue Bold", 10), bg = bgColor, command = self.resetTime).pack(padx=5, pady=5, side=Tkinter.TOP)

        miniFrame.pack(pady=0, fill = Tkinter.X)
        miniFrame2.pack(pady=5, fill = Tkinter.X)
        Frame1.pack(padx=5, pady=pady, side=Tkinter.TOP)

        #Frame2.pack(padx=5, pady=pady, side=Tkinter.TOP)
        self.FrameLeft.grid(row = 0, column = 0, columnspan = 1, rowspan = 100, padx = 5, stick = "new")

        self.root.withdraw()
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - self.root.winfo_reqwidth()) / 2
        y = (self.root.winfo_screenheight() - self.root.winfo_reqheight()) / 2
        self.root.geometry("+{0}+{1}".format(x, y))
        self.root.resizable(False,False)
        self.loaded = True
        self.autoPlot()
        self.recordTimer()
        self.plotArea.bind('<Motion>', self.motion)
        self.plotArea.bind('<Button-1>', self.mouseClick)
        self.plotArea.bind('<ButtonRelease-1>', self.mouseClickRelease)

        self.root.deiconify()
        self.root.mainloop()

    def numFishChanged(self, varname, elementname, mode):
        if self.killUpdates:
            return
        self.updateNumFish()

    def updateNumFish(self, force = False ):

        self.filterChanged()
        numFish =  int(self.numFishToShow.get())
        col = 0
        for fishIndex in range(self.maxNumFish):
            if fishIndex < numFish:
                if fishIndex % 3 == 0 and fishIndex > 0:
                    col += 1    
                self.FishFrames[fishIndex].grid(row = fishIndex % 3, column = col, columnspan = 1, rowspan = 1, padx = 5, pady = 5, stick = "new")
            else:
                self.FishFrames[fishIndex].grid_forget()
        if self.loaded:
            self.drawAll()

    def createFish(self ):
        numFish =  self.maxNumFish
        self.stepsToKeep = []
        self.whichFilter = []
        self.whichDistortion = []
        self.filterOption = []
        self.distortionOption = []
        self.fishVar = []
        self.fishOption = []
        bgColor = "#EDEDED"
        for fishIndex in range(numFish):
            Tkinter.Label(self.FishFrames[fishIndex], text = "Path " + str(fishIndex + 1), font=("Helvetica Neue Bold", 12), bg = bgColor).pack(pady=0, fill = Tkinter.X)

            miniFrame = Tkinter.Frame(self.FishFrames[fishIndex], borderwidth = 1,bg=bgColor)
            Tkinter.Label(miniFrame, text = "Path Length (Seconds)", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=0, side=Tkinter.LEFT)
            self.stepsToKeep.append(Tkinter.StringVar(self.root))
            Tkinter.Spinbox(miniFrame, from_=1, to=100000, width=5,textvariable = self.stepsToKeep[fishIndex], command = self.pastStepsChanged).pack(padx=5,side=Tkinter.LEFT)
            self.stepsToKeep[fishIndex].set("15")
            miniFrame.pack(fill = Tkinter.X)

            #Which filter to use
            miniFrame = Tkinter.Frame(self.FishFrames[fishIndex], borderwidth = 1, bg=bgColor)
            Tkinter.Label(miniFrame, text = "Filter", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=15, side=Tkinter.LEFT)
            choices = ['None', 'Averaging', 'Kalman Filter', 'Corner Cut']
            self.whichFilter.append(Tkinter.StringVar(self.root))
            self.whichFilter[fishIndex].set('None')
            self.filterOption.append(Tkinter.OptionMenu(miniFrame, self.whichFilter[fishIndex], *choices))
            self.filterOption[-1].configure(state = "disabled")
            self.filterOption[fishIndex].pack(padx=5, pady=0, side=Tkinter.LEFT)
            self.whichFilter[fishIndex].trace(mode="w", callback=self.filterChanged)

            Tkinter.Label(miniFrame, text = "Distortion", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=15, side=Tkinter.LEFT)
            choicesDistortion = ['None', 'Jitter']
            self.whichDistortion.append(Tkinter.StringVar(self.root))
            self.whichDistortion[fishIndex].set('None')
            self.distortionOption.append(Tkinter.OptionMenu(miniFrame, self.whichDistortion[fishIndex], *choicesDistortion))
            self.distortionOption[-1].configure(state = "disabled")
            self.distortionOption[fishIndex].pack(padx=5, pady=0, side=Tkinter.LEFT)
            self.whichDistortion[fishIndex].trace(mode="w", callback=self.filterChanged)

            miniFrame.pack(pady=0, fill = Tkinter.X)

            #Which fish to track
            miniFrame = Tkinter.Frame(self.FishFrames[fishIndex], borderwidth = 1, bg=bgColor)
            Tkinter.Label(miniFrame, text = "Fish to Track", font=("Helvetica Neue Bold", 10), bg = bgColor).pack(padx=5, pady=15, side=Tkinter.LEFT)
            self.fishVar.append(Tkinter.StringVar(self.root))
            self.fishVar[fishIndex].set(self.fishTagList[0])
            self.fishOption.append(Tkinter.OptionMenu(miniFrame, self.fishVar[fishIndex], *self.fishTagList))
            self.fishVar[fishIndex].trace(mode="w", callback=self.fishChanged)
            self.fishOption[fishIndex].pack(padx=5, pady=0, side=Tkinter.LEFT)
            miniFrame.pack(pady=0, fill = Tkinter.X)

            #self.FishFrames[fishIndex].pack(padx=5, pady=10)

    def reverseButtonPress(self):
        self.playing = False
        self.reversing = True

    def playButtonPress(self):
        self.playing = True
        self.reversing = False

    def pauseButtonPress(self):
        self.playing = False
        self.reversing = False
        pass

    def pastStepsChanged(self):
        if self.loaded:
            self.drawAll()
    def SkipTo(self):
        year =self.gotoYear.get()
        month = self.gotoMonth.get()
        day = self.gotoDay.get()
        hour = self.gotoHour.get()
        minute = self.gotoMinute.get()
        second = self.gotoSecond.get()

        try:
            self.currentTime = datetime.datetime(int(year),int(month),int(day), int(hour),int(minute),int(second))
        except:
            print "invalid time"

    def resetTime(self):
        self.currentTime = self.beginTime
        self.drawAll()
        self.updateSetTime(force = True)

    def Exit(self):
        self.root.destroy()

    def Restart(self):
        print "Reset"
        self.plotArea.delete("all")

        if self.imgPhoto is not None:
            self.backgroundImage = self.plotArea.create_image(self.width/2,self.height/2, image=self.imgPhoto)

    def fishChanged(self, varname = None, elementname = None, mode = None):
        if self.killUpdates:
            return
        if not self.fileLoaded:
            return
        print "Enter Fish Changed"
        self.pointsForEachFishBox = []
        for fishIndex in range(int(self.numFishToShow.get())):
            if self.fishVar[fishIndex].get() == 'No Fish File Loaded':
                print "Skipping"
                continue
            print "Loading new fish:", self.fishVar[fishIndex].get()
            self.pointsForEachFishBox.append(self.fish[self.fishVar[fishIndex].get()])
            self.pointsForEachFishBox[-1] = np.array(self.pointsForEachFishBox[-1])
        #self.Restart()
        print "calling"
        self.filterChanged()
        print "Exit fish Changed"

    def filterChanged(self, varname = None, elementname = None, mode = None, force = False):
        if self.killUpdates:
            return
        if not self.fileLoaded:
            return
        #If we set the kalman filter, we need to run it on that trace's points
        print "Reloading points"
        self.pointsForEachFishBox = []
        for fishIndex in range(int(self.numFishToShow.get())):
            try:
                self.pointsForEachFishBox.append(self.fish[self.fishVar[fishIndex].get()])
            except:
                return
        
        for fishIndex in range(int(self.numFishToShow.get())):

            if self.whichDistortion[fishIndex].get() == "Jitter":
                fishTag = self.fishVar[fishIndex].get()
                if not self.restoring:
                    loadingScreen = LoadingScreen(self.root, "Applying Jitter Distortion...")
                    loadingScreen.grab_set()
                jitter = jitter_points(self.pointsForEachFishBox[fishIndex], 5.0)
                self.pointsForEachFishBox[fishIndex] = jitter
                if not self.restoring:
                    loadingScreen.destroy()

            if self.whichFilter[fishIndex].get() == 'Kalman Filter':
                fishTag = self.fishVar[fishIndex].get()
                if fishTag in self.cachedKalmanFilters.keys() and self.whichDistortion[fishIndex].get() == "None":
                    print "Loading cached kalman filter values for fish with tag", fishTag
                    self.pointsForEachFishBox[fishIndex] = self.cachedKalmanFilters[fishTag]
                else:
                    loadingScreen = LoadingScreen(self.root, "Applying Kalman Filter...")
                    loadingScreen.grab_set()
                    kalman = kalman_filter(self.pointsForEachFishBox[fishIndex])
                    self.pointsForEachFishBox[fishIndex] = kalman
                    if self.whichDistortion[fishIndex].get() == "None":
                        self.cachedKalmanFilters[fishTag] = kalman
                    loadingScreen.destroy()
            if self.whichFilter[fishIndex].get() == "Corner Cut" and self.whichDistortion[fishIndex].get() == "None":
                fishTag = self.fishVar[fishIndex].get()
                if fishTag in self.cachedCornerFilters.keys():
                    print "Loading cached corner cut filter values for fish with tag", fishTag
                    self.pointsForEachFishBox[fishIndex] = self.cachedCornerFilters[fishTag]
                else:
                    cornercut = corner_cut(self.pointsForEachFishBox[fishIndex], 2)
                    self.pointsForEachFishBox[fishIndex] = cornercut
                    if self.whichDistortion[fishIndex].get() == "None":
                        self.cachedCornerFilters[fishTag] = cornercut
        if self.loaded:
            self.drawAll()

    def filterPoint(self, index, fishIndex):
        if self.recording:
            return self.recordedPoints[index]
        points = self.pointsForEachFishBox[fishIndex]
        if self.whichFilter[fishIndex].get() == "Averaging":
            bufferSize = 3
            start = max(0, index - bufferSize)
            end = min(len(points)-1, index + bufferSize)
            pointsSubset = np.array(points[start: end])
            pointsSubset = pointsSubset[:, 0:2].astype(float)

            x = np.mean(pointsSubset[:,0])
            y = np.mean(pointsSubset[:,1])

            return np.array([x, y])
        else:
            return np.array(points[index][0:2]).astype(float)

    def drawAll(self):
        if not self.fileLoaded and not self.recording:
            return
        self.plotArea.delete("all")

        if self.imgPhoto is not None:
            self.backgroundImage = self.plotArea.create_image(self.width/2,self.height/2, image=self.imgPhoto)

        if self.recording:
            stepsToKeep = len(self.recordedPoints)
            index = len(self.recordedPoints)
            stop = len(self.recordedPoints) -2

            for behind in range( max(0, index - stepsToKeep), min(index, stop)):
                colorHex = self.colors[0]
                firstPoint = self.filterPoint(behind, 0)
                secondPoint = self.filterPoint(behind + 1, 0)
                self.plotArea.create_line(firstPoint[0], firstPoint[1],secondPoint[0],secondPoint[1], fill=colorHex, width = 2)
            return

        if len(self.allTimes) < 1:
            return

        #Calculate Current Index for each fish and plot
        for fishIndex in range(int(self.numFishToShow.get())):
            tailLength = int(self.stepsToKeep[fishIndex].get())
            #points = np.array(points)
            #times = points[:,3]
            times = self.allTimes[fishIndex]

            ct = self.currentTime
            i = len(times)/2
            realIndex = i

            #Binary search
            while(True):

                if ct < times[i]:  
                    times = times[0:len(times)/2]
                    realIndex = realIndex - len(times) 
                else:
                    times = times[len(times)/2 : len(times)]
                    realIndex = realIndex + len(times)/2

                i = len(times)/2
                realIndex += i
                if len(times) < 2:
                    break
            index = realIndex
            pastIndex = realIndex
            times = self.allTimes[fishIndex]
            stopTime = self.currentTime - datetime.timedelta(seconds=int(tailLength))
            if index == 0:
                continue

            while(True):
                if pastIndex >= len(times):
                    pastIndex = len(times) -1
                    continue
                if times[pastIndex] < stopTime:
                    break
                pastIndex -= 1
                if pastIndex < 1:
                    break
                
            
            stop = len(self.pointsForEachFishBox[fishIndex]) -2

            if self.whichFilter[fishIndex].get() == "Corner Cut" and not self.recording:
                index = index * 4
                pastIndex = pastIndex * 4
            for behind in range( max(0, pastIndex), min(index, stop)):
                colorHex = self.colors[fishIndex]
                firstPoint = self.filterPoint(behind, fishIndex)
                secondPoint = self.filterPoint(behind + 1, fishIndex)

                #print "plotting at", firstPoint[0], firstPoint[1]

                self.plotArea.create_line(firstPoint[0], firstPoint[1],secondPoint[0],secondPoint[1], fill=colorHex, width = 2)

    def updateSetTime(self, force = False):
        if self.playing or self.reversing or force:
            self.gotoYear.set(str(self.currentTime.year))
            self.gotoMonth.set(str(self.currentTime.month))
            self.gotoDay.set(str(self.currentTime.day))
            self.gotoHour.set(str(self.currentTime.hour))
            self.gotoMinute.set(str(self.currentTime.minute))
            self.gotoSecond.set(str(self.currentTime.second))

    def rescale(self, fish):
        maxHeight = self.height
        middleBarrierSize = self.width / 40
        maxWidth = self.width / 2 - middleBarrierSize
        maxHeightInData = 0.0
        maxWidthInData = 0.0
        for tag in fish:
            for point in fish[tag]:
                maxWidthInData = max(point[0], maxWidthInData)
                maxHeightInData = max(point[1], maxHeightInData)

        scaleY = maxHeight / float(maxHeightInData)
        scaleX = maxWidth / float(maxWidthInData)
        for tag in fish:
            for point in fish[tag]:
                if point[2] == "Synthetic Data":
                    break
                point[0] = point[0] * scaleX
                point[1] = point[1] * scaleY

        #Reset cached filters
        self.cachedKalmanFilters = {}
        self.cachedCornerFilters = {}


    def openFile(self, fileToOpen = None):
        self.Newfish = {}
        
        if fileToOpen is None:
            self.readfile = tkFileDialog.askopenfile(parent = self.root ,mode='rb',title='Choose a file')
        else:
            self.readfile = fileToOpen
        loadingScreen = LoadingScreen(self.root, "Loading File...")
        loadingScreen.grab_set()


        if self.readfile is None:
            loadingScreen.destroy()
            print "Open fish data file canceled by user"
            return

        self.fishDataFilenameDisplay.set("Loading file...")

        self.Newfish = read_and_sort_csv(self.readfile.name)
        if self.Newfish is None:
            loadingScreen.destroy()
            print "Invalid CSV file - expecting format similar to trial1data.csv - 1.5"
            tkMessageBox.showinfo("Error", "Error reading \"" + self.readfile.name + "\". This error may be due to trying to read a file other than a cvs file. Another cause for this error is that the cvs file must have exactly 10 columns in the following order \"TagCode\",\"Date\",\"Time\",\"Easting\",\"Northing\",\"DateTime\",\"Period\",\"Period2\",\"Species\",\"Trial\". The column names do not matter, as long as there are 10 and that the TagCode, Easting, Northing, and Species data are in the 1st, 4th, 5th, and 9th columns respectively.")
            return

        self.rescale(self.Newfish)

        #self.fish = merge_two_dicts(self.fish, self.Newfish)
        self.fish = self.Newfish
        self.fishTagList = self.fish.keys()

        for fishIndex in range(self.maxNumFish):
            self.fishOption[fishIndex]['menu'].delete(0, 'end')    

            for tag in self.fishTagList:
                self.fishOption[fishIndex]['menu'].add_command(label=tag, command=Tkinter._setit(self.fishVar[fishIndex], tag))

        del self.pointsForEachFishBox
        self.pointsForEachFishBox = []
        self.killUpdates = True
        for fishIndex in range(self.maxNumFish):
            self.fishVar[fishIndex].set(self.fishTagList[0])
            self.pointsForEachFishBox.append(self.fish[self.fishVar[fishIndex].get()])


        self.fishDataFilenameDisplay.set(ntpath.basename("a file"))
        self.fileLoaded = True

        for fishIndex in range(self.maxNumFish):
            self.filterOption[fishIndex].configure(state = "normal")
            self.distortionOption[fishIndex].configure(state = "normal")

        firstDateTimes = []
        lastDateTimes = []
        for aFish in self.fish:
            firstDateTimes.append(self.fish[aFish][0][3])
            lastDateTimes.append(self.fish[aFish][-1][3])
        self.currentTime = min(firstDateTimes)
        self.beginTime =  min(firstDateTimes)
        self.endTime =  max(lastDateTimes)
        self.beginTime = self.beginTime - datetime.timedelta(seconds = 1)
        self.endTime = self.endTime + datetime.timedelta(seconds = 1)
        self.currentTime = self.beginTime
        self.currentTimeTK.set(str(self.currentTime.strftime("%Y-%m-%d %H:%M:%S")))

        #Reset cached filters
        self.cachedKalmanFilters = {}
        self.cachedCornerFilters = {}
        self.numPoints = len(self.pointsForEachFishBox[0])
        self.allTimes = []
        for fishIndex in range(self.maxNumFish):
                points = np.copy(self.pointsForEachFishBox[fishIndex])
                try:
                    self.allTimes.append(points[:,3])
                except:
                    pass
        self.killUpdates = False
        self.updateSetTime(force = True)
        self.drawAll()
        loadingScreen.destroy()
        self.filemenu.entryconfig("Save State", state="normal")

    def autoPlot(self):
        if self.recording:
            self.root.after(50, self.autoPlot)
            return
        try:
            autostepAmount = float(self.timeMultiplierVar.get())
        except ValueError:
            print "AutoStep adjusted" 

        self.root.after(50, self.autoPlot)
        try:
            multiplier = float(self.timeMultiplierVar.get())
        except:
            multiplier = 1.0
        if self.playing:
            self.currentTime =  self.currentTime + datetime.timedelta(milliseconds=int(50 * multiplier))
        elif self.reversing:
            self.currentTime =  self.currentTime - datetime.timedelta(milliseconds=int(50 * multiplier))

        if self.currentTime > self.endTime:
            self.currentTime = self.endTime
        if self.currentTime < self.beginTime:
            self.currentTime = self.beginTime
        self.currentTimeTK.set(str(self.currentTime.strftime("%Y-%m-%d %H:%M:%S")))
        self.drawAll()
        self.updateSetTime()

    def loadBackgroundImage(self):
        file = tkFileDialog.askopenfile(parent = self.root ,mode='rb',title='Choose a file')
        loadingScreen = LoadingScreen(self.root, "Rescaling Data")
        if file is None:
            loadingScreen.destroy()
            print "Could not find file"
            return

        try:
            imgPil = Image.open(file.name)
            self.rawBackground = imgPil
        except:
            loadingScreen.destroy()
            tkMessageBox.showinfo("Error", "Error reading image file. Only jpg and png images are supported.")
            return
        self.width, self.height = imgPil.size
        self.imgPhoto = ImageTk.PhotoImage(imgPil)
        self.backgroundImage = self.plotArea.create_image(self.width/2,self.height/2, image=self.imgPhoto)
        self.plotArea.config(width=self.width, height=self.height)
        if self.fish:
            self.rescale(self.fish)
        self.Restart()

        loadingScreen.destroy()

    def setColumState(self, state):

        #Disable left column iteratively
        for child in self.FrameLeft.winfo_children():
            try:
                child.configure(state=state)
            except:
                pass
            for cc in child.winfo_children():
                try:
                    cc.configure(state=state)
                except:
                    pass
                for ccc in cc.winfo_children():
                    try:
                        ccc.configure(state=state)
                    except:
                        pass
        #Disable right column
        for child in self.FrameRight.winfo_children():
            try:
                child.configure(state=state)
            except:
                pass
            for cc in child.winfo_children():
                try:
                    cc.configure(state=state)
                except:
                    pass
                for ccc in cc.winfo_children():
                    try:
                        ccc.configure(state=state)
                    except:
                        pass
                    for cccc in ccc.winfo_children():
                        try:
                            cccc.configure(state=state)
                        except:
                            pass
    def record(self):
        self.recordCurrentTime = datetime.datetime.now()
        self.plotArea.delete("all")
        if self.imgPhoto is not None:
            self.backgroundImage = self.plotArea.create_image(self.width/2,self.height/2, image=self.imgPhoto)
        self.recordedPoints = []
        self.recordIndex = 0
        self.setColumState("disabled")
        self.recordMenu.entryconfig("Finish Recording Data", state="normal")
        self.filemenu.entryconfig("Open Fish Data File", state="disabled")
        self.filemenu.entryconfig("Load Background Image", state="disabled")
        self.recordMenu.entryconfig("Start Recording Data", state="disabled")
        self.filemenu.entryconfig("Save State", state="disabled")
        self.filemenu.entryconfig("Restore State", state="disabled")
        #self.recordMenu.entryconfig("Add Jitter Noise", state="normal")
        
        recordingScreen = RecordingScreen(self.root, self)
        recordingScreen.grab_set()
        self.root.wait_window(recordingScreen)
        self.drawAll()
        if self.recording == False:
            self.finishRecording(cancel = True)
        self.recordTimer()

    def finishRecording(self, cancel = False):
        self.setColumState("normal")
        self.recordMenu.entryconfig("Finish Recording Data", state="disabled")
        self.filemenu.entryconfig("Open Fish Data File", state="normal")
        self.filemenu.entryconfig("Load Background Image", state="normal")
        self.recordMenu.entryconfig("Start Recording Data", state="normal")
        #self.recordMenu.entryconfig("Add Jitter Noise", state="disabled")
        self.filemenu.entryconfig("Save State", state="normal")
        self.filemenu.entryconfig("Restore State", state="normal")

        self.plotArea.delete("all")
        self.recording = False
        if self.imgPhoto is not None:
            self.backgroundImage = self.plotArea.create_image(self.width/2,self.height/2, image=self.imgPhoto)

        self.mousex = None

        if cancel:
            return
        f = tkFileDialog.asksaveasfile(mode='w', defaultextension=".csv")
        if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
            return
        write_points(self.recordedPoints, f.name, tag = self.recordTagName)
        askOpenNow = AskOpenNow(self.root, self)
        askOpenNow.grab_set()
        self.root.wait_window(askOpenNow)

        if self.saveNow:
            self.openFile(fileToOpen = f)
            self.resetTime()
        else:
            if self.fileLoaded:
                self.filemenu.entryconfig("Save State", state="normal")
            else:
                self.filemenu.entryconfig("Save State", state="disabled")
        self.drawAll()

    def recordTimer(self):

        if self.recording:
            if self.mousex is None or not self.mouseDown:
                self.root.after(20, self.recordTimer)
                return

            self.recordCurrentTime =  self.recordCurrentTime + datetime.timedelta(milliseconds=int(50 * float(self.recordInterval)))
            self.recordedPoints.append([self.mousex, self.mousey, str(self.recordCurrentTime.strftime("%Y-%m-%d %H:%M:%S.%f"))])
            self.drawAll()
            self.recordIndex = self.recordIndex + 1
            self.root.after(20, self.recordTimer)
            
    def motion(self, event):
        #print event.state
        if self.recording:
            self.mousex = event.x
            self.mousey = event.y

    def showHelpMenu(self):
        helpScreen = HelpScreen(self.root)
        helpScreen.grab_set()

    def showAboutMenu(self):
        helpScreen = AboutScreen(self.root)
        helpScreen.grab_set()
    def create_window(self):
        t = Tkinter.Toplevel(self.root)
        t.wm_title("Window #%s" % 0)
        l = Tkinter.Label(t, text="This is window #%s" % 10)
        l.pack(side="top", fill="both", expand=True, padx=100, pady=100)

    def jitterRecording(self):
        prompJitterScreen = PrompJitterScreen(self.root, self)
        prompJitterScreen.grab_set()
        self.root.wait_window(prompJitterScreen)
        if self.jitterAmount == -1:
            return
        self.recordedPoints = jitter_points(np.array(self.recordedPoints), self.jitterAmount)
        self.drawAll()

    def saveState(self):
        saveFile = tkFileDialog.asksaveasfile(mode='w', defaultextension=".fvs")

        if saveFile is None:
            return

        print "Saving"
        self.playing = False
        self.reversing = False

        loadingScreen = LoadingScreen(self.root, "Saving State...")
        loadingScreen.grab_set()

        saveDict = {}
        saveDict['fileLoaded'] = self.fileLoaded
        saveDict['pointsForEachFishBox'] = self.pointsForEachFishBox
        saveDict['loaded'] = self.loaded

        saveDict['fish'] = self.fish
        saveDict['cachedKalmanFilters'] = self.cachedKalmanFilters
        saveDict['cachedCornerFilters'] = self.cachedCornerFilters
        saveDict['fishTagList'] = self.fishTagList
        saveDict['width'] = self.width
        saveDict['height'] = self.height
        saveDict['rawBackground'] = self.rawBackground
        saveDict['endTime'] = self.endTime
        saveDict['beginTime'] = self.beginTime
        saveDict['currentTime'] = self.currentTime

        saveDict['beginTime'] = self.beginTime

        saveDict['whichFilter'] = []
        for fishIndex in range(self.maxNumFish):
            saveDict['whichFilter'].append(self.whichFilter[fishIndex].get())

        saveDict['whichDistortion'] = []
        for fishIndex in range(self.maxNumFish):
            saveDict['whichDistortion'].append(self.whichDistortion[fishIndex].get())

        saveDict['fishVar'] = []
        for fishIndex in range(self.maxNumFish):
            saveDict['fishVar'].append(self.fishVar[fishIndex].get())

        saveDict['numFishToShow'] = self.numFishToShow.get()
        saveDict['timeMultiplierVar'] = self.timeMultiplierVar.get()

        saveDict['stepsToKeep'] = []
        for fishIndex in range(self.maxNumFish):
            saveDict['stepsToKeep'].append(self.stepsToKeep[fishIndex].get())

        saveDict['allTimes'] =  self.allTimes

        pickle.dump(saveDict, open(saveFile.name, "wb"))
        print "Done Saving"
        loadingScreen.destroy()


    def restoreState(self):
        self.killUpdates = True
        self.restoring = True
        print "Restoring"
        self.playing = False
        self.reversing = False
        restoreFile = tkFileDialog.askopenfile(parent = self.root ,mode='rb',title='Choose a file')
        if restoreFile is None:
            print "Restore state canceled by user"
            return

        loadingScreen = LoadingScreen(self.root, "Loading Saved State...")
        loadingScreen.grab_set()

        try:
            saveDict = pickle.load(open(restoreFile.name, "rb"))
        except:
            loadingScreen.destroy()
            tkMessageBox.showinfo("Error", "The file \"" + restoreFile.name  + "\" is not a valid save state. This could be caused by trying to load a save state created by an older version of this program.")

            return

        self.fileLoaded = saveDict['fileLoaded']  
        self.pointsForEachFishBox = saveDict['pointsForEachFishBox']  
        self.loaded = saveDict['loaded'] 

        self.fish = saveDict['fish'] 
        self.cachedKalmanFilters = saveDict['cachedKalmanFilters'] 
        self.cachedCornerFilters = saveDict['cachedCornerFilters']
        self.fishTagList = saveDict['fishTagList'] 
        self.width = saveDict['width'] 
        self.height = saveDict['height'] 
        self.beginTime = saveDict['beginTime']
        self.endTime = saveDict['endTime']
        self.currentTime = saveDict['currentTime']
        self.allTimes = saveDict['allTimes']
        if saveDict['rawBackground'] is not None:
            self.imgPhoto = ImageTk.PhotoImage(saveDict['rawBackground'])
        else:
            self.imgPhoto = None
        self.numFishToShow.set(saveDict['numFishToShow'])
        self.timeMultiplierVar.set(saveDict['timeMultiplierVar'])

        for fishIndex in range(self.maxNumFish):
            self.whichFilter[fishIndex].set(saveDict['whichFilter'][fishIndex])

        for fishIndex in range(self.maxNumFish):
            self.whichDistortion[fishIndex].set(saveDict['whichDistortion'][fishIndex])

        for fishIndex in range(self.maxNumFish):
            self.fishVar[fishIndex].set(saveDict['fishVar'][fishIndex])


        for fishIndex in range(self.maxNumFish):
            self.filterOption[fishIndex].configure(state = "normal")
            self.distortionOption[fishIndex].configure(state = "normal")

        for fishIndex in range(self.maxNumFish):
            self.fishOption[fishIndex]['menu'].delete(0, 'end')    
            for tag in self.fishTagList:
                self.fishOption[fishIndex]['menu'].add_command(label=tag, command=Tkinter._setit(self.fishVar[fishIndex], tag))

        for fishIndex in range(self.maxNumFish):
            self.stepsToKeep[fishIndex].set(saveDict['stepsToKeep'][fishIndex])

        self.killUpdates = False
        self.updateNumFish(force = True)
        self.fishChanged()
        self.drawAll()

        self.updateSetTime(force = True)

        print "Done Restoring"
        loadingScreen.destroy()
        self.restoring = False
        self.filemenu.entryconfig("Save State", state="normal")

    def mouseClick(self, event):
        self.mouseDown = True

    def mouseClickRelease(self, event):
        self.mouseDown = False

    def on_closing(self):
        self.root.destroy()
	
# Calling the class will execute our GUI.
App(points)
os._exit(0)

