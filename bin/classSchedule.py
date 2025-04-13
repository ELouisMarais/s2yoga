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
# -----------------------------------------------------------------------------
# Version: 0.0.12
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
# Version: 0.0.13
# Author: Louis Marais
# Start date: 2025-03-30
# Last modifications: 2025-04-06
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Check datetime.conf file to get start time for the schedule depending on
#    date of the year, instead of using the hard-coded bits.
# 2. Removed the process lock bits of code as this program only runs once so
#    the process lock parts are not required for correct functioning of the
#    program.
# 3. Redone some of the code such as formatting (.format ... to f-strings.
#
# -----------------------------------------------------------------------------
# Version: 0.0.14
# Author: Louis Marais
# Start date: 2025-04-13
# Last modifications: 2025-04-13
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Bug fix, humidity in 2nd cycle should be 50 %RH, was set to 55 %RH
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

import os
import time
import sys
import argparse
import configparser
import re
import datetime

script = os.path.basename(__file__)
VERSION = "0.0.13"
AUTHORS = "Louis Marais"

DEBUG = False

weekdays = ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY',
						'SUNDAY']
months = ['January','February','March','April','May','June','July','August',
					'September','October','November','December']

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
	print(f'ERROR: {s}')
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
			errorExit(f'Required key ({s}) not in configuration file.')
	debug("All required section:key pairs found in configuration file.")
	return(cnt)

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
def loadSchedule(flnm):
	debug(f"Reading class schedule from {flnm}")
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
					errorExit(f"Invalid day of week in line {lines.index(line)} "+
							 f"of {flnm}: {m.groups()[0]}")
				if not (checktime(tm)):
					errorExit(f"Invalid time specificed in line {lines.index(line)} "+
							 f"of {flnm}: {line}")
				schedule.append([dy,tm,temp,hum])
			else:
				errorExit(f"Invalid entry found in {flnm} line {lines.index(line)}: "+
							f"{line.strip()}")
	debug(f"Schedule read successfully. Found {len(schedule)} classes.")
	return(schedule)

# -----------------------------------------------------------------------------
# convert minutes to hh:mm
def formatTime(t):
	hr = t // 60
	mn = t - (hr*60)
	s = f"{hr:02d}:{mn:02d}"
	return(s)

# -----------------------------------------------------------------------------
# The following preheat sequence is used:
#
# @ preheat time: t = 25, h = 55
# @ preheat time + 30: t = setT - 5, h = 50
# @ preheat time + 45: t = setT,     h = setH
#
def createClass(set_vals,st_tms,prht_tms):
	dy = set_vals[0]
	t = set_vals[1].split(':')
	hr = int(t[0])
	tm = hr * 60 + int(t[1])
	temp = set_vals[2]
	hum = set_vals[3]
	for i in range(0,len(st_tms)):
		if hr < st_tms[i]:
				prht_tm = prht_tms[i]
				break
	# Each programme has four entries, the last one is to set the temperature
	# back (i.e. turn off the heat and humidity)
	tmStr = formatTime(tm - prht_tm)
	newprgm = [f"{dy:10s} {tmStr} {25:9.1f} {55:10.1f}"]
	tmStr = formatTime(tm - prht_tm + 30)
	newprgm.append(f"{dy:10s} {tmStr} {temp-5:9.1f} {50:10.1f}")
	tmStr = formatTime(tm - prht_tm + 45)
	newprgm.append(f"{dy:10s} {tmStr} {temp:9.1f} {hum:10.1f}")
	# For 6 am classes, set temperature 1 degC higher for floor
	# series ~ 45 minutes into the class.
	if (hr == 6):
		tmStr = formatTime(tm + 45)
		newprgm.append(f"{dy:10s} {tmStr} {temp+1:9.1f} {hum:10.1f}")
	tmStr = formatTime(tm + 95)
	newprgm.append(f"{dy:10s} {tmStr} {21:9.1f} {20:10.1f}")
	return (newprgm)

# -----------------------------------------------------------------------------
# For debugging, print the settings nicely
def printSettings(lst):
	print('\n-----  START of class settings --------\n')
	for l in lst:
		print(l)
	print('\n-----  END of class settings ----------\n')
	return

# -----------------------------------------------------------------------------
def createTHsettings(programme,strts,prhts):
	c = 0
	n = len(programme)
	settings = ['MONDAY     00:00      21.0       20.0']
	min_t = [   # Time between classes - to decide how to plan the classes.
		47/1440,  # 45 (47) minutes
		107/1440  # 105 (107) minutes
		]
	for i in range(0,len(programme)):
		settings.extend(createClass(programme[i],strts,prhts))
	debug("Temperature and humidity settings created from class schedule.")
	# For debugging...
	#printSettings(settings)
	return(settings)

# -----------------------------------------------------------------------------
def saveSettingsFile(schedule,flnm):
	header = [
	 '# A file to keep the settings that are required for the temperature /'+
	 ' humidity',
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
			f.write(f"{h}\n")
		for c in schedule:
			f.write(f"{c}\n")
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
				s = f"{dy:<11s}{th:02d}:{tm:02d}{temp:10.1f}{hum:11.1f}"
				ths[i] = s
	debug("Temperature and Humidity settings corrected for overlapping times.")
	return(ths)

# -----------------------------------------------------------------------------
def makedate(day,mnth):
	yr = time.localtime().tm_year
	dy = int(day)
	mn = months.index(mnth)+1
	tmst = time.mktime(datetime.datetime(year=yr,month=mn,day=dy).timetuple())
	dt = int(tmst/86400) + 40587 # MJD 'like' date
	return(dt)

# -----------------------------------------------------------------------------
def getDateTimeSettings(fl,dt):  # Get settings on or after 'dt'
	cnf = configparser.ConfigParser()
	cnf.read(fl)
	req = ['main,dates','defaults,startday','defaults,startmonth',
				'defaults,times','defaults,preheat']
	dtcnf = checkConfig(cnf, req)
	chks = [s.strip() for s in list(cnf['main']['dates'].split(','))]
	newdates = [makedate(cnf['defaults']['startday'],cnf['defaults']['startmonth'])]
	sdts = [cnf['defaults']['startday']]
	smnt = [cnf['defaults']['startmonth']]
	times = [cnf['defaults']['times']]
	preheats = [cnf['defaults']['preheat']]
	for itm in chks:
		reqs = ['startday','startmonth','times','preheat']
		for r in reqs:
			if not r in cnf[itm]:
				errorExit(f"{r} not in {itm}")
		newdates.append(makedate(cnf[itm]['startday'],cnf[itm]['startmonth']))
		sdts.append(cnf[itm]['startday'])
		smnt.append(cnf[itm]['startmonth'])
		times.append(cnf[itm]['times'])
		preheats.append(cnf[itm]['preheat'])
	# find date on or after dt
	cdt = newdates[0]
	idx = -1
	for i in range(0,len(newdates)):
		if dt >= newdates[i]:
			debug(f"Possible start date for new settings: {sdts[i]} {smnt[i]}")
			debug(f"     Settings for {newdates[i]}, it is larger or equal to {dt}")
			cdt = newdates[i]
			tms = times[i]
			phs = preheats[i]
			idx = i
	# Create lists of start and preheat times for programming the schedule.
	st_times = []
	ph_times = []
	l = [s.strip() for s in tms.split(',')]
	for k in l:
		try:
			t = int(k)
		except:
			msg =  f"Settings file: {fl}\n"
			msg +=  "       There is an error in the start time list for "
			msg += f"{sdts[idx]} {smnt[idx]}\n"
			msg += f"       Start times list: {times[idx]}\n"
			errorExit(msg)
		if t >= 0 and t <= 24:
			st_times.append(t)
	l = [s.strip() for s in phs.split(',')]
	for k in l:
		try:
			t = int(k)
		except:
			msg =  f"Settings file: {fl}\n"
			msg +=  "       There is an error in the preheat times list for "
			msg += f"{sdts[idx]} {smnt[idx]}\n"
			msg += f"       Preheat times list: {preheats[idx]}\n"
			errorExit(msg)
		if t >= 0 and t <= 360: # Maximum preheat period is 360 minutes (6 hours)
			ph_times.append(t)
	if not len(st_times) == len(ph_times):
		msg =  f"Settings file: {fl}\n"
		msg += f"       The lengths of the start hours ({len(st_times)}) and pre-heat "
		msg += f"times ({len(ph_times)}) are not equal!\n"
		msg += "       The error is for this date in the settings file: "
		msg += f"{sdts[idx]} {smnt[idx]}\n"
		msg += f"       Start times list: {times[idx]}\n"
		msg += f"       Preheat times list: {preheats[idx]}\n"
		errorExit(msg)
	return(st_times,ph_times)

# -----------------------------------------------------------------------------
def makeFilename(hm,fl):
	if not fl.startswith('/'):
		fl = hm + fl
	return(fl)

# -----------------------------------------------------------------------------
def getCurrentDate(): # Something like MJD, but not quite (uses localtime, not gmtime)
	yr = time.localtime().tm_year
	mn = time.localtime().tm_mon
	dy = time.localtime().tm_mday
	tmst = time.mktime(datetime.datetime(year=yr,month=mn,day=dy).timetuple())
	dt = int(tmst/86400) + 40587
	return(dt)

# -----------------------------------------------------------------------------
def getDateFromStr(s):
	lst = s.split()
	d = int(lst[0])
	m = lst[1]
	return(d,m)

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
parser.add_argument("-t","--testdate",nargs=1,help="Specify a date to create "+
										"a settings file for. Date must be in format 'd Month'")
parser.add_argument("-d","--debug",action="store_true",
										help="Turn debugging on")

args = parser.parse_args()

if args.debug:
	DEBUG = True

versionStr = f"{script} version {VERSION} written by {AUTHORS}"

if args.version:
	print(versionStr)
	sys.exit(0)

debug(versionStr)

HOME = os.path.expanduser('~')
if not(HOME.endswith('/')):
	HOME += '/'

debug(f"Current user's home: {HOME}")

configfile = f"{HOME}etc/classSchedule.conf"

if args.config:
	debug(f"Alternate config file specified: {str(args.config[0])}")
	configfile = str(args.config[0])
	if not configfile.startswith('/'):
		configfile = HOME+configfile

debug("Configuration file: "+configfile)

if not os.path.isfile(configfile):
	errorExit(configfile+' does not exist.')

sDate = getCurrentDate()

if args.testdate:
	debug(f"Test date: {args.testdate[0]}")
	(dy,mn) = getDateFromStr(args.testdate[0])
	sDate = makedate(dy,mn)

conf = configparser.ConfigParser()
conf.read(configfile)

req = ['main,settings file','main,datetime settings']

cfg = checkConfig(conf, req)

debug(f"conf['main']['settings file'] = {conf['main']['settings file']}")
debug(f"conf['main']['datetime settings'] = {conf['main']['datetime settings']}")

# The file to save the temp hum settings that is set by the control program.
settingsfile = makeFilename(HOME,conf['main']['settings file'])

debug("Settings file: "+settingsfile)

schedulefile = ""
if conf['schedule']['file']:
	schedulefile = makeFilename(HOME,conf['schedule']['file'])
	debug("Found a class schedule in the configuration: {}".format(schedulefile))
	if not os.path.isfile(schedulefile):
		schedulefile = ""
		debug("Ignoring the class schedule in the configuration as it does not exists.")

dtsettingsflnm = makeFilename(HOME,conf['main']['datetime settings'])

if not os.path.isfile(dtsettingsflnm):
	errorExit(f"{dtsettingsflnm} does not exist.")

debug(f"Date and Time settings file: {dtsettingsflnm}")

start_tms,preheat_tms = getDateTimeSettings(dtsettingsflnm,sDate)

schedule = loadSchedule(schedulefile)

thsettings = createTHsettings(schedule,start_tms,preheat_tms)

thsettings = checkTHsettings(thsettings)

# For debugging...
#printSettings(thsettings)

saveSettingsFile(thsettings,settingsfile)

debug(f'{script} terminated.')
