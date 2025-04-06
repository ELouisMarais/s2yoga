#!/usr/bin/python3
# checkSchedule.py

# This will regularly check the file specified in the settings file
# (classSchedule.conf) and if its modification time changed will
# run the classSchedule.py script to create a new settings file
# for the control of temperature and humidity in the studio.

# -----------------------------------------------------------------------------
# Version: 0.1
# Author: Louis Marais
# Start date: 2024-03-02
# Last modifications: 2024-03-10
#
# Modifications:
# ~~~~~~~~~~~~~~
# Initial version
#
# -----------------------------------------------------------------------------
# Version: 0.2
# Author: Louis Marais
# Start date: 2025-03-29
# Last modifications: 2025-04-06
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Redone some of the code such as formatting (.format ... to f-strings.
# 2. Now also checks the ~/etc/datetime.conf file to see if the
#    temphum.settings file must be updated because the start times have
#    changed due to the date (old Summer / Winter change hard coded into the
#    <binfile> (nominally "classSchedule.py" program). That program was also
#    changed.
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
import datetime
import sys
import argparse
import configparser
import signal
import subprocess

script = os.path.basename(__file__)
VERSION = "0.1"
AUTHORS = "Louis Marais"

months = ['January','February','March','April','May','June','July','August',
					'September','October','November','December']

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
	print(f'ERROR: {s}')
	sys.exit(1)

# -----------------------------------------------------------------------------
def checkConfig(cfg, req):
	cnt = []
	for section in cfg.sections():
		s = section.lower()
		for key in cfg[section]:
			cnt.append(f'{s},{key.lower()}')
	for s in req:
		if not s in cnt:
			errorExit(f'Required key ({s}) not in configuration file.')
	debug("All required section:key pairs found in configuration file.")
	return(cnt)

# -----------------------------------------------------------------------------
def TestProcessLock(lockFile):
	if (os.path.isfile(lockFile)):
		flock=open(lockFile,'r')
		info = flock.readline().split()
		flock.close()
		if (len(info)==2):
			if (os.path.exists(f'/proc/{str(info[1])}')):
				return False
	return True

# -----------------------------------------------------------------------------
def CreateProcessLock(lockFile):
	if (not TestProcessLock(lockFile)):
		return False;
	flock=open(lockFile,'w')
	flock.write(f'{os.path.basename(sys.argv[0])} {str(os.getpid())}')
	flock.close()
	return True

# -----------------------------------------------------------------------------
def RemoveProcessLock(lockFile):
	if (os.path.isfile(lockFile)):
		os.unlink(lockFile)
	return

# -----------------------------------------------------------------------------
def signalHandler(signal,frame):
	global running
	running = False
	debug("User / system request for program termination.")
	return

# -----------------------------------------------------------------------------
def makeFilename(hm,fl):
	if not fl.startswith('/'):
		fl = hm + fl
	return(fl)

# -----------------------------------------------------------------------------
def makedate(day,mnth):
	yr = time.localtime().tm_year
	dy = int(day)
	mn = months.index(mnth)+1
	tmst = time.mktime(datetime.datetime(year=yr,month=mn,day=dy).timetuple())
	dt = int(tmst/86400) + 40587 # MJD 'like' date
	return(dt)

# -----------------------------------------------------------------------------
def readTDconf(fl,oldt):  # oldt is the date when the program was last changed
	cnf = configparser.ConfigParser()
	cnf.read(fl)
	req = ['main,dates','defaults,startday','defaults,startmonth',
				'defaults,times','defaults,preheat']
	dtcnf = checkConfig(cnf, req)
	chks = [s.strip() for s in list(cnf['main']['dates'].split(','))]
	newdates = [makedate(cnf['defaults']['startday'],cnf['defaults']['startmonth'])]
	for itm in chks:
		reqs = ['startday','startmonth','times','preheat']
		for r in reqs:
			if not r in cnf[itm]:
				errorExit(f"{r} not in {itm}")
		newdates.append(makedate(cnf[itm]['startday'],cnf[itm]['startmonth']))
	debug(f"Dates in time date config: {newdates}")
	# Return next date that program has to change
	dt = 0
	for d in newdates:
		if oldt < d:
			dt = d
			break
	debug(f"Program to be updated on {dt}")
	return(dt)

# -----------------------------------------------------------------------------
def getCurrentDate(): # Something like MJD, but not quite (uses localtime, not gmtime)
	yr = time.localtime().tm_year
	mn = time.localtime().tm_mon
	dy = time.localtime().tm_mday
	tmst = time.mktime(datetime.datetime(year=yr,month=mn,day=dy).timetuple())
	dt = int(tmst/86400) + 40587
	#debug(f"Current date {dt}")
	return(dt)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Checks class schedule, and if "+
																 "it has been modified runs the script that "+
																 "creates the temp hum settings file for "+
																 "control of the hot room")
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

versionStr = f"{script} version {VERSION} written by {AUTHORS}"

if args.version:
	print(versionStr)
	sys.exit(0)

debug(versionStr)

HOME = os.path.expanduser('~')
if not(HOME.endswith('/')):
	HOME += '/'

debug(f"Current user's home :{HOME}")

configfile = f"{HOME}etc/classSchedule.conf"

if args.config:
	debug(f"Alternate config file specified: {str(args.config[0])}")
	configfile = str(args.config[0])

	if not configfile.startswith('/'):
		configfile = HOME+configfile

debug(f"Configuration file: {configfile}")

if not os.path.isfile(configfile):
	errorExit(f"{configfile} does not exist.")

conf = configparser.ConfigParser()
conf.read(configfile)

req = ['main,datetime settings','checker,lock file','schedule,file',
			 'checker,bin file']

cfg = checkConfig(conf, req)

debug(f"conf['main']['datetime settings'] = {conf['main']['datetime settings']}")
debug(f"conf['checker']['lock file'] = {conf['checker']['lock file']}")
debug(f"conf['schedule']['file'] = {conf['schedule']['file']}")
debug(f"conf['checker']['bin file'] = {conf['checker']['bin file']}")

dtSettingsFile = makeFilename(HOME,conf['main']['datetime settings'])

debug(f"Date time settings file: {dtSettingsFile}")

schflnm = makeFilename(HOME,conf['schedule']['file'])

debug(f"Class schedule file: {schflnm}")

if not os.path.isfile(schflnm):
	errorExit('The class schedule file does not exist.')

binfile = makeFilename(HOME,conf['checker']['bin file'])

debug(f"Executable to run: {binfile}")

if not os.path.isfile(binfile):
	errorExit("The binary file that you are supposed to run does not exist...")

lockfile = makeFilename(HOME,conf['checker']['lock file'])

debug(f"Lock file: {lockfile}")

if not CreateProcessLock(lockfile):
	errorExit(f'Unable to lock - {script} already running?')

signal.signal(signal.SIGINT,signalHandler)
signal.signal(signal.SIGTERM,signalHandler)
signal.signal(signal.SIGHUP,signalHandler) # not usually run with a controlling
                                           # TTY, but handle it anyway

running = True
fmod_old = 0
updateDate = 0
fmod_td_old = 0
updateRequired = False
updatedDate = getCurrentDate()

while running:
	# Was the class program changed?
	fmod = os.path.getmtime(schflnm)
	if not fmod == fmod_old:
		fmod_old = fmod
		debug("Schedule file updated. New settings file required.")
		updateRequired = True
	# Do we need to re-read the date time configuration file?
	fmod = os.path.getmtime(dtSettingsFile)
	if not fmod == fmod_td_old:
		debug("Time and date settings file updated. New settings file required.")
		debug(f"Old update date: {updateDate}")
		updateDate = readTDconf(dtSettingsFile,updatedDate)
		fmod_td_old = fmod
		updateRequired = True
	# Is an update required because of the date?
	currentDate = getCurrentDate()
	if updateDate <= currentDate:
		debug(f"Current date: {currentDate}, Update date: {updateDate}")
		updateRequired = True
	if updateRequired:
		cmd = [binfile]
		retval = subprocess.run(cmd,capture_output = True)
		if retval.returncode == 0:
			debug("Settings file successfully created")
		else:
			print(f"Executable: {binfile}")
			print(f"Return code: {retval.returncode}")
			print(f"Std out: {retval.stdout.decode('ascii')}")
			print(f"Std err: {retval.stderr.decode('ascii')}")
			print("ERROR: Could not create settings file.")
			break  # Have to remove the lock file!
		updatedDate = currentDate
		updateRequired = False
		debug(f"settings file updated on {updatedDate}")
		# If this update was required because of the date, a new update date is
		# required. For ease of use, the date is updated every time an update is
		# done.
		updateDate = readTDconf(dtSettingsFile,updatedDate)
	time.sleep(0.5)

RemoveProcessLock(lockfile)

debug(f'{script} terminated.')
