#!/usr/bin/python3
# classSchedule.py

# A script to generate the temphum.settings file for the studio to
# eliminate the need to manually edit the program.
#
# A Qt6 appplication (runs on windows and linux) generates a class schedule.
# Another application that runs continuously and checks for a change in the
# modification time of the schedule file (copied to the ~/tmp directory on
# the server. When this file changes, it runs this script that creates a new
# settings file.
#
# -----------------------------------------------------------------------------
# Ver: 0.0.1
# Author: Louis Marais
# Start: 2024-01-13
# Last: 2024-01-28
#
# -----------------------------------------------------------------------------
# Ver: 0.0.2
# Author: Louis Marais
# Start: 2024-03-03
# Last: 2024-03-16
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Scrapped the idea of this program also handling the class scheduling. A
#    Qt6 program running on the Windows laptop creates the class schedule and
#    another script looks for  a change in the schedule file that is scp'ed
#    to the server and then calls this script that creates the new settings
#    file (despite the name...)
# 2. Changed settings creation routine to take care of temperatures and
#    humidities as read from the class schedule file.
#
# -----------------------------------------------------------------------------
# Ver: 0.0.3
# Author: Louis Marais
# Start: 2024-03-24
# Last: 2024-03-24
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Karen asked for the 6 am classes to start heating an hour before the class
#    so I am making that change.
# 2. She also wants the heat to go up 1 degree an hour into the 6 am class, so
#    I am adding that too, but not activating it...
#
# -----------------------------------------------------------------------------
# Version: 0.0.4
# Author: Louis Marais
# Start date: 2024-04-21
# Last modifications: 2024-04-21
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Karen asked for the studio to start heating up earlier. She wants all the
#    times to move up 30 minutes.
# 2. We talked and decided to split the timings. Summer and Winter. Winter
#    timings start 1 April and ends 1 October.
# 3. The way it works now the schedule will need to be updated at these two
#    times to allow the control software to create the appropriate settings
#    file.
#
# -----------------------------------------------------------------------------
# Version: 0.0.5
# Author: Louis Marais
# Start date: 2024-04-28
# Last modifications: 2024-04-28
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Changed timings again because Karen asked me. For classes that start
#    earlier than 12:00.
#
# -----------------------------------------------------------------------------
# Version: 0.0.6
# Author: Louis Marais
# Start date: 2024-05-24
# Last modifications: 2024-05-24
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Changed timings again. Karen asked that the heaters come on 15 minutes
#    earlier than for the previous version for early classes.
#
# -----------------------------------------------------------------------------
# Version: 0.0.7
# Author: Louis Marais
# Start date: 2024-06-04
# Last modifications: 2024-06-04
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Changed timings again. Karen wanted all classes to start heating
#    20 minutes earlier.
#
# -----------------------------------------------------------------------------
# Version: 0.0.8
# Author: Louis Marais
# Start date: 2024-06-13
# Last modifications: 2024-06-13
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Changed timings again. Karen wanted all classes to start heating
#    30 additional minutes earlier.
#
# -----------------------------------------------------------------------------
# Version: 0.0.9
# Author: Louis Marais
# Start date: 2024-08-25
# Last modifications: 2024-08-25
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Changed timings. From 20 Aug make heating times 45 minutes later. Yes,
#    it is getting warmer.
#
# -----------------------------------------------------------------------------
# Version: 0.0.10
# Author: Louis Marais
# Start date: 2024-09-02
# Last modifications: 2024-09-02
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Rolled back part of the change. Changed the 45 minutes to 15 minutes.
#
# -----------------------------------------------------------------------------
# Version: 0.0.11
# Author: Louis Marais
# Start date: 2024-10-06
# Last modifications: 2024-10-06
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Changed the date when the times goes to Summer time from 20 September to
#    20 October, because 20 September is too early.
#
# TODO: Decided to rewrite the program to use settings that set the preheat
#       times for different dates of the year. This way the program does not
#       need to be modified when the program preheats changes...
#       Major version number change required! And extensive testing.
#
# -----------------------------------------------------------------------------
# Version: 0.0.11
# Author: Louis Marais
# Start date: 2024-10-26
# Last modifications: 2024-10-26
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Changed the date when the times goes to Summer time from 20 October to
#    20 November, because I have not had time to do the new software yet. And
#    the 1 hr 40 min earlier is still a bit too much
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
## -----------------------------------------------------------------------------
import os
import time
import sys
import argparse
import configparser
import re
import datetime

script = os.path.basename(__file__)
VERSION = "0.0.11"
AUTHORS = "Louis Marais"

DEBUG = False

weekdays = ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY']

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
def checkConfig(cfg, req):
	cnt = []
	for section in cfg.sections():
		s = section.lower()
		for key in cfg[section]:
			cnt.append(s+','+key.lower())
	for s in req:
		if not s in cnt:
			errorExit('Required key ({}) not in configuration file.'.format(s))
	debug("All required section:key pairs found in configuration file.")
	return(cnt)

# -----------------------------------------------------------------------------
def TestProcessLock(lockFile):
	if (os.path.isfile(lockFile)):
		flock=open(lockFile,'r')
		info = flock.readline().split()
		flock.close()
		if (len(info)==2):
			if (os.path.exists('/proc/'+str(info[1]))):
				return False
	return True

# -----------------------------------------------------------------------------
def CreateProcessLock(lockFile):
	if (not TestProcessLock(lockFile)):
		return False;
	flock=open(lockFile,'w')
	flock.write(os.path.basename(sys.argv[0]) + ' ' + str(os.getpid()))
	flock.close()
	return True

# -----------------------------------------------------------------------------
def RemoveProcessLock(lockFile):
	if (os.path.isfile(lockFile)):
		os.unlink(lockFile)
	return

# -----------------------------------------------------------------------------
# No sanity checks required, we KNOW 't' is in the right format
def gettime(t):
	hr = int(t[0:2])
	mn = int(t[3:])
	return(hr,mn)

# -----------------------------------------------------------------------------
# Simple check to make sure a time makes sense
def checktime(t):
	hr,mn = gettime(t)
	if (hr < 24) and (mn < 60):
		return(True)
	return(False)

# -----------------------------------------------------------------------------
def calcTimes(dy,hr,mn,offst,temp,hum):
	ts = hr*60+mn + offst
	th = int(ts//60)
	tm = ts-th*60
	return "{:<11s}{:02d}:{:02d}{:10.1f}{:11.1f}".format(dy,th,tm,temp,hum)

# -----------------------------------------------------------------------------
def loadSchedule(flnm):
	debug("Reading class schedule from {}".format(flnm))
	schedule = []
	# Load the class schedule file if it exists
	if os.path.isfile(flnm):
		with open(flnm,"r") as f:
			lines = f.readlines()
			f.close()
		# Read schedule from lines in the file
		p = re.compile(r'(\w+)\s+(\d\d:\d\d)\s+(\d+.\d+)\s+(\d+.\d+)')
		for line in lines:
			if line.strip() == "":
				continue
			if line.strip().startswith('#'):
				continue
			m = re.match(p,line.strip())
			if m:
				dy = m.groups()[0].upper()
				tm = m.groups()[1]
				temp = float(m.groups()[2])
				hum = float(m.groups()[3])
				if not dy in weekdays:
					errorExit("Invalid day of week in line {} of {}: {}".
							 format(lines.index(line),flnm,m.groups()[0]))
				if not (checktime(tm)):
					errorExit("Invalid time specificed in line {} of {}: {}".
							 format(lines.index(line),flnm,line))
				schedule.append([dy,tm,temp,hum])
			else:
				errorExit("Invalid entry found in {} line {}: {}".
							format(flnm,lines.index(line),line.strip()))
	debug("Schedule read successfully. Found {} classes.".
			 format(len(schedule)))
	return(schedule)

# -----------------------------------------------------------------------------
def dayTime(s):
	d = weekdays.index(s[0])
	t = (int(s[1][0:2])*60.0 + int(s[1][3:]))/1440.0
	dt = d+t
	return(dt)

# -----------------------------------------------------------------------------
def getpreheattimes(hr,mn):
	# Between 10 April and 20 September increase preheat 2 & 3 times by 30
	# minutes.
	preheat_tm1 = 60 + 60  # minutes
	preheat_tm2 = 60 + 30  # minutes
	preheat_tm3 = 45       # minutes
	td = time.localtime()
	doy = td.tm_yday
	apr10 = int(datetime.datetime(td.tm_year,4,10,12,0,0).strftime('%j'))
	#sep20 = int(datetime.datetime(td.tm_year,9,20,12,0,0).strftime('%j'))
	# ver 0.0.11  Found that 20 Sep was too early to revert; made it 20 Oct
	sep20 = int(datetime.datetime(td.tm_year,11,20,12,0,0).strftime('%j'))
	if doy >= apr10 and doy <= sep20:
		#print("Increasing preheat times from: ")
		#print(preheat_tm1,preheat_tm2,preheat_tm3)
		# ver 0.0.4 added the additional 30 minutes
		# ver 0.0.7 increased ALL class heating by an additional 20 minutes.
		# ver 0.0.8 increased ALL class heating by an additional 30 minutes.
		# ver 0.0.9 DEcreased ALL class heating by 45 minutes.
		# ver 0.0.10 INcreased ALL class heating by 30 minutes (rolling back
		#            part of the change made in ver 0.0.9
		# We need to set more windows ...
		preheat_tm1 += 30 + 20 + 30 - 45 + 30
		preheat_tm2 += 30 + 20 + 30 - 45 + 30
		preheat_tm3 += 30 + 20 + 30 - 45 + 30
		debug("Date between 10 April and 20 September. Preheat times increased "+
				"by 30 + 20 + 30 - 45 + 30 minutes")
		# ver 0.0.5 added the additional 45 minutes for classes that start before 12
		# ver 0.0.6 increased the additional time to 60 minutes
		if hr < 12:
			preheat_tm1 += 60
			preheat_tm2 += 60
			preheat_tm3 += 60
			debug("Date between 10 April and 20 September and class starts before"+
					  " 12. Preheat times increased by an additional 60 minutes")
	#print("Original times:",preheat_tm1,preheat_tm2,preheat_tm3)
	if (hr == 6) and (mn == 0):
		preheat_tm1 += 15
		preheat_tm2 += 15
		preheat_tm3 += 15
		debug("Class starts at 06:00 - heating time made 15 minutes earlier!")
		#print("Updated times:",preheat_tm1,preheat_tm2,preheat_tm3)
	return(preheat_tm1,preheat_tm2,preheat_tm3)

# -----------------------------------------------------------------------------
def norm_program(cls):
	debug("Creating normal program for this class: {}".format(cls))
	dy = cls[0]
	hr = int(cls[1][0:2])
	mn = int(cls[1][3:])
	t = cls[2]
	h = cls[3]
	(preheat_tm1,preheat_tm2,preheat_tm3) = getpreheattimes(hr,mn)
	prgm = []
	# Preheat time 1 before class set to 25 degrees, 55 %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm1,25.0,55.0))
	# Preheat time 2 before class set to setpoint -5 degrees, 50 %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm2,t-5,50.0))
	# Preheat time 3 before class set to setpoint degrees, setpoint %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm3,t,h))
	# Up temperature by 1 degree if this is an early class
	if (hr == 6) and (mn == 0):
		prgm.append(calcTimes(dy,hr,mn,+45,t+1,h))
	# 5 minutes after class set to 21 degrees, 20 %RH
	prgm.append(calcTimes(dy,hr,mn,95,21.0,20.0))
	return prgm

# -----------------------------------------------------------------------------
def two_programs(cls1,cls2):
	debug("Creating a program for two classes following close together:")
	debug("  Class 1: {}".format(cls1))
	debug("  Class 2: {}".format(cls2))
	dy = cls1[0]
	hr = int(cls1[1][0:2])
	mn = int(cls1[1][3:])
	t = cls1[2]
	h = cls1[3]
	(preheat_tm1,preheat_tm2,preheat_tm3) = getpreheattimes(hr,mn)
	prgm = []
	# Preheat time 1 before class1 set to 25 degrees, 55 %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm1,25.0,55.0))
	# Preheat time 2 before class1 set to setpoint -5 degrees, 50 %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm2,t-5,50.0))
	# Preheat time 3 before class1 set to setpoint degrees, setpoint %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm3,t,h))
	# Up temperature by 1 degree if this is an early class
	# Then set it back 5 miutes after end of class
	if (hr == 6) and (mn == 0):
		prgm.append(calcTimes(dy,hr,mn,+45,t+1,h))
		prgm.append(calcTimes(dy,hr,mn,+95,t,h))
	# Class 2
	dy = cls2[0]
	hr = int(cls2[1][0:2])
	mn = int(cls2[1][3:])
	# 5 minutes after class2 set to 21 degrees, 20 %RH
	prgm.append(calcTimes(dy,hr,mn,95,21.0,20.0))
	return prgm

# -----------------------------------------------------------------------------
def hybrid_programs(cls1,cls2):
	debug("Creating a hybrid program for two classes close together (> 30 min, <= 90 min):")
	debug("  Class 1: {}".format(cls1))
	debug("  Class 2: {}".format(cls2))
	dy = cls1[0]
	hr = int(cls1[1][0:2])
	mn = int(cls1[1][3:])
	t = cls1[2]
	h = cls1[3]
	(preheat_tm1,preheat_tm2,preheat_tm3) = getpreheattimes(hr,mn)
	prgm = []
	# Preheat time 1 before class1 set to 25 degrees, 55 %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm1,25.0,55.0))
	# Preheat time 2 before class1 set to setpoint -5 degrees, 50 %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm2,t-5,50.0))
	# Preheat time 3 before class1 set to setpoint degrees, setpoint %RH
	prgm.append(calcTimes(dy,hr,mn,-preheat_tm3,t,h))
	# Up temperature by 1 degree if this is an early class
	if (hr == 6) and (mn == 0):
		prgm.append(calcTimes(dy,hr,mn,+45,t+1,h))
	# 5 minutes after class1 set to setpoint -5 degrees, 40 %RH
	prgm.append(calcTimes(dy,hr,mn,95,t-5,40.0))
	# Class 2
	dy = cls2[0]
	hr = int(cls2[1][0:2])
	mn = int(cls2[1][3:])
	t = cls2[2]
	h = cls2[3]
	# 45 minutes before class1 set to setpoint degrees, setpoint %RH
	prgm.append(calcTimes(dy,hr,mn,-45,t,h))
	# 5 minutes after class2 set to 21 degrees, 20 %RH
	prgm.append(calcTimes(dy,hr,mn,95,21.0,20.0))
	return prgm

# -----------------------------------------------------------------------------
# When developing a class schedule, consider 2 classes each time
# 1. If the difference between the end time of class 1 and the start of class 2
#    is less or equal to 45 minutes keep the temperature as it was set at the
#    start of class 1 until the end of class 2
# 2. If this difference is less than 105 minutes, keep the temperature at 35
#    celsius until 45 minutes before the start of class 2
# 3. If the difference is > 105 minutes follow the 'normal' program schedule
#
# Normal program schedule:
# 1. Set to 21 celsius, 20 %RH, Monday 00:00                   DP: -2.8 celsius
# 2. Set to 25 celsius, 55 %RH, 105 minutes before class start DP: 15.3 celsius
# 3. Set to {temp-5} celsius, 50 %RH, 90 minutes before class start DP: 23.0
#    celsius
# 4. Set to {temp} celsius, {hum} %RH, 45 minutes before class start DP: {calc}
#    celsius
# 5. Set to 21 celsius, 20 %RH, 5 minutes after class ends    DP: -2.8 celsius
#
# Special cases (added for ver 0.0.3)
# 1. For 6 am classes, start heating 1 hour before the time (not 45 minutes).
# 2. For 6 am classes, increase temperature 1 degree in middle of the class.
#
def createTHsettings(programme):
	#print("programme\n\n",programme)
	c = 0
	n = len(programme)
	settings = ['MONDAY     00:00      21.0       20.0']
	min_t = [
		47/1440, # 45 (47) minutes
		107/1440  # 105 (107) minutes
		]
	while True:
		d1 = dayTime(programme[c])
		d2 = 99 # Make it unreasonable large (max = 7 for calculated value)
		if c < n-1:
			d2 = dayTime(programme[c+1])
			c += 1
		c += 1
		# if times far enough apart only create program for one class, increase c by 1
		# otherwise create program covering both classes, increase c by 2
		# dif = start of class 2 - end of class 1
		dif = d2 - (d1 + 105/1440)
		if dif < min_t[0]:
			settings.extend(two_programs(programme[c-2],programme[c-1]))
		elif dif < min_t[1]:
			settings.extend(hybrid_programs(programme[c-2],programme[c-1]))
		else:
			settings.extend(norm_program(programme[c-2]))
			# roll back one count
			if (c-1) >= n-1:
				# Prepare normal schedule for class2
				settings.extend(norm_program(programme[c-1]))
			else:
				c -= 1
		if c > n-1:
			break
	return(settings)

# -----------------------------------------------------------------------------
def saveSettingsFile(schedule,flnm):
	# if file exists, ask user if it is OK to overwrite
	# TODO: Add a check if file exists, warn user, overwrite warning if ignored, etc.
	# Create the file header
	header = [
	 '# A file to keep the settings that are required for the temperature / humidity',
	 '# control of the room.',
	 '#',
	 '# Columns:',
	 '# Day of Week (Monday .. Sunday)',
	 '# Start time (HH:MM)',
	 '# Temperature (dd.d) in degree Celsius',
	 '# Humidity (hh.h) in % relative humidity',
	 '',
	 '#         Start    Temperature  Humidity',
	 '# DoW      Time      (deg C)     (%RH)'
	 ]
	# write content
	with open(flnm,'w') as f:
		for h in header:
			f.write("{}\n".format(h))
		for c in schedule:
			f.write("{}\n".format(c))
		f.close()
	return

# -----------------------------------------------------------------------------
def checkTHsettings(ths):
	ths_fixed = [ths[0]]
	p = re.compile(r'(\w+)\s+(\d+):(\d+)\s+(\d+.\d+)\s+(\d+.\d+)')
	for i in range(1,len(ths)):
		f = ths[i-1]
		g = ths[i]
		m1 = re.match(p,f)
		m2 = re.match(p,g)
		if m1.groups()[0] == m2.groups()[0]:
			ts1 = int(m1.groups()[1])*60 + int(m1.groups()[2])
			ts2 = int(m2.groups()[1])*60 + int(m2.groups()[2])
			#print(ts1,ts2)
			if ts1 > ts2:
				dy = m2.groups()[0]
				ts3 = ts1 + 1
				th = ts3//60
				tm = ts3 - th*60
				temp = float(m2.groups()[3])
				hum = float(m2.groups()[4])
				s = "{:<11s}{:02d}:{:02d}{:10.1f}{:11.1f}".format(dy,th,tm,temp,hum)
				#print(f)
				#print(g)
				#print(s,'\n')
				ths[i] = s
		#else:
		#	ths_fixed.append(g)
	return(ths)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Reads class schedule, allows "+
																 "modifications and saving to a user selected "+
																 "file name, then generates the settings file")
parser.add_argument("-v","--version",action="store_true",help="Show version "+
										"and exit.")
parser.add_argument("-c","--config",nargs=1,help="Specify alternative "+
										"configuration file. The default is "+
										"~/etc/classSchedule.conf.")
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

HOME = os.path.expanduser('~')
if not(HOME.endswith('/')):
	HOME += '/'

debug("Current user's home :"+HOME)

configfile = HOME+"etc/classSchedule.conf"

if args.config:
	debug("Alternate config file specified: "+str(args.config[0]))
	configfile = str(args.config[0])
	if not configfile.startswith('/'):
		configfile = HOME+configfile

debug("Configuration file: "+configfile)

if not os.path.isfile(configfile):
	errorExit(configfile+' does not exist.')

conf = configparser.ConfigParser()
conf.read(configfile)

req = ['main,lock file','main,settings file']

cfg = checkConfig(conf, req)

debug("conf['main']['lock file'] = {}".format(conf['main']['lock file']))
debug("conf['main']['settings file'] = {}".format(conf['main']['settings file']))

lockfile = conf['main']['lock file']

if not lockfile.startswith('/'):
	lockfile = HOME+lockfile

debug("Lock file: "+lockfile)

settingsfile = conf['main']['settings file']

if not settingsfile.startswith('/'):
	settingsfile = HOME+settingsfile

debug("Settings file: "+settingsfile)

schedulefile = ""
if conf['schedule']['file']:
	schedulefile = conf['schedule']['file']
	if not schedulefile.startswith('/'):
		schedulefile = HOME+schedulefile
	debug("Found a class schedule in the configuration: {}".format(schedulefile))
	if not os.path.isfile(schedulefile):
		schedulefile = ""
		debug("Ignoring the class schedule in the configuration as it does not exists.")

if not CreateProcessLock(lockfile):
	errorExit('Unable to lock - '+script+' already running?')

schedule = loadSchedule(schedulefile)
thsettings = createTHsettings(schedule)

thsettings = checkTHsettings(thsettings)

# Create the temperature / humidity settings file
saveSettingsFile(thsettings,settingsfile)

RemoveProcessLock(lockfile)

debug('{} terminated.'.format(script))
