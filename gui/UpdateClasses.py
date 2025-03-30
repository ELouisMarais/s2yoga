#!/usr/bin/python3
# UpdateClasses.py

# A script to generate the class schedule file for the studio that runs on the
# Windows computer. This works in conjunction with scripts on the server to
# generate the temphum.settings file that controls the studio environment.
#
# To generate an executable, you need pyinstaller.
#   Install:  pip install -U pyinstaller
#
# Create an executable (see pyinstaller.org):
#
#   pyinstaller UpdateClasses.py
#
#   The executable will be here:
#   ~\dist\UpdateClasses\UpdateClasses.exe
#
# Note: The virus software will likely object to running these bits of software
#       but will eventually agree that all is well.
#
# -----------------------------------------------------------------------------
# Ver: 1.0
# Author: Louis Marais
# Start: 2024-02-25
# Last: 2024-03-10
#
# -----------------------------------------------------------------------------
# Version: {Next}
# Author:
# Start date:
# Last modifications:
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1.
#
# -----------------------------------------------------------------------------

from PyQt6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
    QGridLayout,
    #QLineEdit,
    QComboBox,
    QMainWindow,
    QFrame,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtGui import QIcon, QFont, QColor, QResizeEvent
from PyQt6.QtCore import Qt

import sys
import re
import subprocess
import tempfile
import os

import time
import argparse
import configparser

# Assign input values for settings table
days = ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY']
times = []
for hours in range(0,24):
    for mins in [0,15,30,45]:
        times.append("{:02d}:{:02d}".format(hours,mins))
temps = []
for i in range(20,45):
    temps.append("{:0.1f}".format(i))
hums = []
for i in range(20,45):
    hums.append("{:0.1f}".format(i))
    
# Set paths
tmp = tempfile.gettempdir()
sep = os.sep
if not tmp.endswith(sep):
    tmp += sep
HOME = os.path.expanduser('~')
if not HOME.endswith(sep):
    HOME += sep

script = os.path.basename(__file__)
VERSION = "1.0"
AUTHORS = "Louis Marais"

DEBUG = False

# -----------------------------------------------------------------------------
def ts():
	return(time.strftime('%Y-%m-%d %H:%M:%S ',time.gmtime()))

# -----------------------------------------------------------------------------
def debug(msg):
	if DEBUG:
		print(ts(),msg)
	return

# -----------------------------------------------------------------------------
def errorExit(s):
	print('ERROR: '+s)
	sys.exit(1)

# -----------------------------------------------------------------------------
# Class definition
# -----------------------------------------------------------------------------

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Set2Yoga class schedule manager")
        self.setWindowIcon(QIcon("logo.png"))
        
        self.generalLayout = QVBoxLayout()
        
        centralWidget = QWidget(self)
        centralWidget.setLayout(self.generalLayout)
        
        self.setCentralWidget(centralWidget)
        
        # Set initial size of window
        self.resize(640,480)
        
        self._createDisplay()
        
        self.loadSettings()
        
        self.showEditConfirmation = True
        
        self.lastClassFile = ""
        
        # Default server values (home server)
        self.user = 'pi'
        self.ip = '192.168.1.93'
        self.serverpath = 'tmp/'
        
    def loadSettings(self):
        global DEBUG
        parser = argparse.ArgumentParser(description="Generate, load, save and "+
			"upload class schedule for Set2Yoga studio.")
        parser.add_argument("-v","--version",action="store_true",help="Show version "+
			"and exit.")
        parser.add_argument("-c","--config",nargs=1,help="Specify alternative "+
			"configuration file. The default is "+
			"{}yogaclass.conf.".format(HOME))
        parser.add_argument("-d","--debug",action="store_true",
			help="Turn debugging on")
        args = parser.parse_args()
        
        if args.debug:
            DEBUG = True
        versionStr = script+" version "+VERSION+" written by "+AUTHORS
        
        if args.version:
            print(versionStr)
            sys.exit(0)
        debug(versionStr)
        self.configfile = HOME+"yogaclass.conf"

        if args.config:
            debug("Alternate config file specified: "+str(args.config[0]))
            self.configfile = str(args.config[0])
            if not self.configfile.startswith(sep): #won't work in Windows...
                self.configfile = HOME+configfile
        
        debug("Configuration file: "+self.configfile)

        if args.version:
            print(versionStr)
            sys.exit(0)
        
        debug(versionStr)
        
        if not os.path.isfile(self.configfile):
            # Tell user no existing file to load.
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Class schedule file")
            dlg.setText("There is no class schedule configuration file. "+
                "Load or create a schedule manually.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
            return
            
        # If there is a schedule file specified in the configuration, load it.
        conf = configparser.ConfigParser()
        conf.read(self.configfile)
        
        if conf.has_option('classes','file'):
            # Check if file exists
            flnm = conf['classes']['file']
            debug("Previous class file: {}".format(flnm))
            if os.path.isfile(flnm):
                # load file
                self.loadFile(flnm)
                self.lastClassFile = flnm
                debug("Loaded classes from {}".format(flnm))
            else:
                debug("No classes found on {}".format(flnm))
    
    def _createDisplay(self):
        global DEBUG
        debug("Creating layout")
        self.middle = QLabel("Middle")
        self.bottom = QLabel("Bottom")
        
        topLayout = QGridLayout()

        self.line0 = QFrame()
        self.line0.setFrameShape(QFrame.Shape.HLine)
        self.line0.setFrameShadow(QFrame.Shadow.Plain)
        
        self.generalLayout.addWidget(self.line0)

        self.lblDay = QLabel("Day",alignment = Qt.AlignmentFlag.AlignCenter)
        self.lblStart = QLabel("Start time",alignment = Qt.AlignmentFlag.AlignCenter)
        self.lblTemp = QLabel("Temperature",alignment = Qt.AlignmentFlag.AlignCenter)
        self.lblHum = QLabel("Humidity",alignment = Qt.AlignmentFlag.AlignCenter)
        self.cmbDay = QComboBox()
        self.cmbStart = QComboBox()
        self.cmbTemp = QComboBox()
        self.cmbHum = QComboBox()
        self.btnAdd = QPushButton("ADD")
        self.btnAdd.clicked.connect(self.Add_clicked)
        
        self.cmbDay.addItems(days)
        self.cmbStart.addItems(times)
        self.cmbTemp.addItems(temps)
        self.cmbHum.addItems(hums)        
        
        topLayout.addWidget(self.lblDay,0,0)
        topLayout.addWidget(self.lblStart,0,1)
        topLayout.addWidget(self.lblTemp,0,2)
        topLayout.addWidget(self.lblHum,0,3)
        topLayout.addWidget(self.cmbDay,1,0)
        topLayout.addWidget(self.cmbStart,1,1)
        topLayout.addWidget(self.cmbTemp,1,2)
        topLayout.addWidget(self.cmbHum,1,3)
        topLayout.addWidget(self.btnAdd,1,4)
        
        self.generalLayout.addLayout(topLayout)
        
        self.line1 = QFrame()
        self.line1.setFrameShape(QFrame.Shape.HLine)
        self.line1.setFrameShadow(QFrame.Shadow.Plain)
        
        self.generalLayout.addWidget(self.line1)
        
        middleLayout = QHBoxLayout()
        
        self.tblSettings = QTableWidget()
        self.tblSettings.setColumnCount(4)
        
        hfont = QFont()
        hfont.setBold(True) # We want BOLD labels
        hlabels = ["DAY","START TIME","TEMP (°C)","HUM (%RH)"]
        self.tblSettings.setHorizontalHeaderLabels(hlabels)
        for i in range(0,len(hlabels)):
            self.tblSettings.horizontalHeaderItem(i).setFont(hfont)
        self.tblSettings.verticalHeader().hide()
        hdr = self.tblSettings.horizontalHeader()
        # Stretch each of the columns so that it fills all the available space.
        hdr.setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
        
        middleLayout.addWidget(self.tblSettings)
        
        self.line2 = QFrame()
        self.line2.setFrameShape(QFrame.Shape.VLine)
        self.line2.setFrameShadow(QFrame.Shadow.Plain)
        
        middleLayout.addWidget(self.line2)        
        
        middleButtons = QVBoxLayout()
        self.btnEdit = QPushButton("EDIT")
        self.btnDel = QPushButton("DELETE")
        
        sze = self.btnDel.minimumSizeHint()
        
        self.btnEdit.resize(sze)
        self.btnDel.resize(sze)
        
        self.btnEdit.clicked.connect(self.Edit_clicked)
        self.btnDel.clicked.connect(self.Del_clicked)
        
        # The addStretch before and after the buttons forces the buttons to be
        # in the middle of the layout.
        # From: https://stackoverflow.com/questions/10082299/qvboxlayout-how-to-vertically-align-widgets-to-the-top-instead-of-the-center
        middleButtons.addStretch()
        middleButtons.addWidget(self.btnEdit)
        middleButtons.addWidget(self.btnDel)
        middleButtons.addStretch()
        
        middleLayout.addLayout(middleButtons)
        
        self.generalLayout.addLayout(middleLayout)
        
        self.line3 = QFrame()
        self.line3.setFrameShape(QFrame.Shape.HLine)
        self.line3.setFrameShadow(QFrame.Shadow.Plain)
        
        self.generalLayout.addWidget(self.line3)
        
        bottomLayout = QGridLayout()
        self.btnLoad = QPushButton("LOAD FILE")
        self.btnSave = QPushButton("SAVE FILE")
        self.btnUpload = QPushButton("UPLOAD to Server")
        
        self.btnLoad.clicked.connect(self.Load_clicked)
        self.btnSave.clicked.connect(self.Save_clicked)
        self.btnUpload.clicked.connect(self.Upload_clicked)
        
        bottomLayout.addWidget(self.btnLoad,0,0)
        bottomLayout.addWidget(self.btnSave,0,1)
        bottomLayout.addWidget(self.btnUpload,0,2)

        self.generalLayout.addLayout(bottomLayout)
        debug("Visual interface completed")
        
    def closeEvent(self,event):
        global DEBUG
        debug("Closing {}".format(script))
        # Save the name of the current file in the settings file
        if self.lastClassFile != "":
            conf = configparser.ConfigParser()
            conf['classes'] = {}
            conf['classes']['file'] = self.lastClassFile
            conf['upload'] = {}
            conf['upload']['user'] = self.user
            conf['upload']['ip'] = self.ip
            conf['upload']['path'] = self.serverpath
            with open(self.configfile,'w') as f:
                conf.write(f)
            debug("Configuration file rewritten: {}".format(self.configfile))
        else:
            debug("No file accessed during this run - configuration not rewritten")
        event.accept()
    
    def sortTable(self,l):
        # Get table as a list of lists and sort it and show it
        # User is responsible to provide a list of lists with the right sizes
        self.tblSettings.setRowCount(len(l))
        
        # Sort the list of lists first
        # Create a timestamp for each class in a new list
        ts = []
        for i in range(0,len(l)):
            tmstmp = days.index(l[i][0]) + (int(l[i][1][:2])*60 + int(l[i][1][3:]))/1440
            ts.append(tmstmp)
        ts.sort()
        # Sort the list of lists using these timestamps
        k = []
        for i in range(0,len(ts)):
            for j in range(0,len(l)):
                tmstmp = days.index(l[j][0]) + (int(l[j][1][:2])*60 + int(l[j][1][3:]))/1440
                if tmstmp == ts[i]:
                    k.append(l[j])
        # Show the sorted list with alternating colours
        for row in range(0,len(k)):
            for col in range(0,len(k[row])):
                item = QTableWidgetItem(k[row][col])
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if row % 2 == 0:
                    item.setBackground(QColor(255,204,203))
                else:
                    item.setBackground(QColor(173,216,230))
                self.tblSettings.setItem(row,col,item)
    
    def Add_clicked(self):
        # Construct a yoga class using the values in the combo boxes
        c = []
        c.append(self.cmbDay.currentText())
        c.append(self.cmbStart.currentText())
        c.append(self.cmbTemp.currentText())
        c.append(self.cmbHum.currentText())
        # Create a list of all the current yoga classes
        # Also check for a duplicate. If the class is already in the schedule,
        # do not add it
        dup = False
        l = []
        for i in range(0,self.tblSettings.rowCount()):
            t = []
            for j in range (0,self.tblSettings.columnCount()):
                t.append(self.tblSettings.item(i,j).text())
            if (c[0] == t[0]) and (c[1] == t[1]):
                dup = True
            l.append(t)
        if dup:
            return
        # Completely clear the table
        for i in range(self.tblSettings.rowCount()-1,-1,-1):
            self.tblSettings.removeRow(i)
        # Add the new class
        l.append(c)
        # Sort and show the class table
        self.sortTable(l)
        # If this was an Edit, change button caption to 'ADD'
        if not self.btnAdd.text() == 'ADD':
            self.btnAdd.setText('ADD')
            # Set the Edit and Delete buttons back to enabled
            self.btnEdit.setDisabled(False)
            self.btnDel.setDisabled(False)
    
    def Edit_clicked(self):
        row = self.tblSettings.currentRow()
        if row < 0: # No cell selected
            return
        s = ""
        for i in range (0,self.tblSettings.columnCount()):
            s += "{:s} ".format(self.tblSettings.item(row,i).text())
        # Set all the comboboxes to the values in the current row
        self.cmbDay.setCurrentText(self.tblSettings.item(row,0).text())
        self.cmbStart.setCurrentText(self.tblSettings.item(row,1).text())
        self.cmbTemp.setCurrentText(self.tblSettings.item(row,2).text())
        self.cmbHum.setCurrentText(self.tblSettings.item(row,3).text())
        # Delete the current item from the schedule
        self.btnAdd.setText("DONE")
        self.showEditConfirmation = False
        self.Del_clicked()
        self.showEditConfirmation = True
        # Set the EDIT and DELETE buttons to not enabled until the edit is done.
        self.btnEdit.setEnabled(False)
        self.btnDel.setEnabled(False)
        
    def Del_clicked(self):
        row = self.tblSettings.currentRow()
        if row < 0:
            return
        s = ""
        for i in range (0,self.tblSettings.columnCount()):
            s += "{:s} ".format(self.tblSettings.item(row,i).text())
        if self.showEditConfirmation:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Confirm")
            dlg.setText("Are you sure you want to delete this class?\n{}".format(s))
            dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            btn = dlg.exec()
            if not btn == QMessageBox.StandardButton.Yes:
                return
        self.tblSettings.removeRow(row)
        # sort table and show
        l = []
        for i in range(0,self.tblSettings.rowCount()):
            t = []
            for j in range (0,self.tblSettings.columnCount()):
                t.append(self.tblSettings.item(i,j).text())
            l.append(t)
        for i in range(self.tblSettings.rowCount()-1,-1,-1):
            self.tblSettings.removeRow(i)
        self.sortTable(l)
        
    def Load_clicked(self):
        # Show file menu
        retv = QFileDialog.getOpenFileName(
                self,
                "Load file",
                "",
                "Text files (*.txt);; All files (*)",
        )
        flnm = retv[0]
        if flnm == '':
            return
        self.loadFile(flnm)
    
    def loadFile(self,flnm):
        with open(flnm,"r") as f:
            lines = f.readlines()
            f.close()
        # Use regular expression to make sure data is in the correct format
        p = re.compile(r'(\w+)\s+(\d+:\d+)\s+(\d+.\d+)\s+(\d+.\d+)\s*')
        l = []
        for line in lines:
            m = re.match(p,line)
            if m:
                if m.groups()[0] in days:
                    s = []
                    for i in range(0,4):
                        s.append(m.groups()[i])
                    l.append(s)
        if len(l) > 0:
            # Completely clear the current table
            for i in range(self.tblSettings.rowCount()-1,-1,-1):
                self.tblSettings.removeRow(i)
            # Load the new table
            self.sortTable(l)
            self.lastClassFile = flnm
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("No useable data")
            dlg.setText("No classes were found in the file ({})".format(flnm))
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            dlg.exec()
     
    def saveSchedule(self,flnm):
        with open (flnm,'w') as f:
            f.write("#DAY  START TIME  TEMP(degC)  HUM(%RH)\n")
            for i in range(0,self.tblSettings.rowCount()):
                s = ""
                for j in range (0,self.tblSettings.columnCount()):
                    s += "{:s}  ".format(self.tblSettings.item(i,j).text())
                s += '\n'
                f.write(s)
            f.close()        
     
    def Save_clicked(self):
        # If class schedule is empty, tell user, and quit this routine
        if self.tblSettings.rowCount() == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("No data!")
            dlg.setText("There is nothing to save.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            btn = dlg.exec()
            return
        # Create a list, save it to a file specified by the user
        retv = QFileDialog.getSaveFileName(
                self,
                "Save file",
                "",
                "Text files (*.txt);; All files (*)",
        )
        if retv[0] == '':
            return
        flnm = retv[0]
        self.saveSchedule(flnm)
        self.lastClassFile = flnm
    
    def Upload_clicked(self):
        # If class schedule is empty, tell user, and quit this routine
        if self.tblSettings.rowCount() == 0:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("No data!")
            dlg.setText("There is nothing to upload to the server.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            btn = dlg.exec()
            return
        # Ask user to confirm the upload
        if self.showEditConfirmation:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Confirm")
            dlg.setText("Are you sure you want to upload this class schedule to the server?")
            dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            btn = dlg.exec()
            if not btn == QMessageBox.StandardButton.Yes:
                return
        # Create a temporary file with the class schedule for uploading
        flnm = tmp + 'classSchedule.txt'
        self.saveSchedule(flnm)
        if os.path.isfile(self.configfile):
            conf = configparser.ConfigParser()
            conf.read(self.configfile)
            if conf.has_option('upload','user'):
                self.user = conf['upload']['user']
            if conf.has_option('upload','ip'):
                self.ip = conf['upload']['ip']
            if conf.has_option('upload','path'):
                self.serverpath = conf['upload']['path']
        
        location = "{}@{}:{}".format(self.user,self.ip,self.serverpath)
        retval = subprocess.run(['scp',flnm,location],capture_output = True)
        # If this asks for a password, see the bit below to set up public / private key
        # exchange between this PC and the server
        if not retval.returncode == 0:
            dlg = QMessageBox(self)
            dlg.setIcon(QMessageBox.Icon.Warning)
            dlg.setWindowTitle("Upload failed!")
            dlg.setText("There was a problem uploading the class schedule to the server.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            btn = dlg.exec()
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Upload successful!")
            dlg.setText("The upload of the class schedule to the server was "+
                "completed successfully.")
            dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
            btn = dlg.exec()
        os.remove(flnm)

# ----------------------------------------------------------------------------- 
# Set up automatic login using a public-private key exchange
# 
#  Create a set of keys on your windows box:
#    Start Windows powershell
#    run 'ssh-keygen.exe'
#    Copy  c:\Users\{Username}\.ssh\id_rsa.pub  to  c:\Users\{Username}\authorized_keys
# 
#  Copy the 'authorized_keys' file to the server:
#    scp authorized_keys {user}@{server_ip}:.ssh/
#
#  Test to see if you can login to the server without supplying a password:
#    ssh {user}@{server_ip}
#    If no password is requested, you are all good. 
#
# ----------------------------------------------------------------------------- 

# ----------------------------------------------------------------------------- 
# Main
# ----------------------------------------------------------------------------- 

def main():
    app = QApplication(sys.argv)
    
    window = Window()
    
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
