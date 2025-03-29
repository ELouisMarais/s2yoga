#!/usr/bin/python3
# temphumlog.py
# A logging script for a Rotronic environmental sensor

# Stolen some routines from envlog.py, a bit of software developed for TF
# with bits stolen from Cryogenics software, but I think these were stolen
# from a time and frequency script in the first place...

# -----------------------------------------------------------------------------
# Ver: 0.0.1
# Author: Louis Marais
# Start: 2023-06-25
# Last: 2023-07-01
#
# -----------------------------------------------------------------------------
# Ver: 0.0.2
# Author: Louis Marais
# Start: 2023-07-16
# Last: 2023-07-16
#
# Modifications:
# --------------
# 1. Save temperature and humidity in a status file for retrieval by eCO2
#    logging program - used to improve estimate of eCO2 (compensate for
#    temperature and humidity)
#
# -----------------------------------------------------------------------------
# Ver: 0.0.3
# Author: Louis Marais
# Start: 2023-08-10
# Last: 2023-08-10
#
# Modifications:
# --------------
# 1. This program blocked completely when the Adafruit IO site went down. I had
#    to do a kill -9 to close it. Restarting the program fixed the issue. But
#    why did this happen?
#
# -----------------------------------------------------------------------------
# Ver: 0.0.4
# Author: Louis Marais
# Start: 2023-12-17
# Last: 2023-12-28
#
# Modifications:
# --------------
# 1. Changed to a control program in addition to a logging program.
#      Simple control - command:
#                                SP tt.t hh.h\n
#      then read back the command to make sure it was delivered correctly
# 2. Removed uploading to Adafruit - now done in separate program.
# 3. Read settings file with DoW, start time, temp, hum
# 4. Added a check for the serial port
# 5. Modified serial port reading routine to accomodate new Arduino serial
#    output (added setpoints and control settings).
#
# -----------------------------------------------------------------------------
# Version: 0.0.5
# Author: Louis Marais
# Start date: 2024-04-21
# Last modifications: 2024-04-21
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Removed some comments, cleaned up a bit. No functional changes.
#
# -----------------------------------------------------------------------------
# Version: 0.1.6
# Author: Louis Marais
# Start date: 2025-02-19
# Last modifications: 2025-0?-??
#
# Modifications:
# ~~~~~~~~~~~~~~
# 1. Added commands for the BOOST option added to the latest hardware
#    controller. New serial command: BOOST [ON|OFF]
# 2. Changed some format strings to f-strings.
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

import serial
import signal
import re
import sys
import datetime
import os
import time
import statistics
import argparse
import configparser
import subprocess
import dateutil.relativedelta

script = os.path.basename(__file__)
VERSION = "0.1.6"
AUTHORS = "Louis Marais"

running = True
DEBUG = False
logcommands = False

numbers = ['0','1','2','3','4','5','6','7','8','9','-']
weekdays = ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY',
						'SUNDAY']

# -----------------------------------------------------------------------------
# Sub routines
# -----------------------------------------------------------------------------
def signalHandler(signal,frame):
	global running
	running = False
	return

# -----------------------------------------------------------------------------
def TestProcessLock(lockFile):
	if (os.path.isfile(lockFile)):
		with open(lockFile,'r') as flock:
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
	with open(lockFile,'w') as flock:
		flock.write(os.path.basename(sys.argv[0]) + ' ' + str(os.getpid()))
		flock.close()
	return True

# -----------------------------------------------------------------------------
def RemoveProcessLock(lockFile):
	if (os.path.isfile(lockFile)):
		os.unlink(lockFile)
	return

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
def makePath(s):
	if not s.startswith('/'):
		s = HOME + s
		if not s.endswith('/'):
			s = s + '/'
	return(s)

# -----------------------------------------------------------------------------
def checkPath(p):
	if not os.path.isdir(p):
		errorExit('The path '+p+' does not exist')
	return

# -----------------------------------------------------------------------------
def makeFilePath(s):
	if not s.startswith('/'):
		s = HOME + s
	return(s)

# -----------------------------------------------------------------------------
def getSensorData(s):
	temp = 9999.9
	hum = 9999.9
	dpnt = 9999.9
	p = re.compile(r'\s*(-*\d+\.\d+) degC,\s*(-*\d+.\d+) %RH,\s*dp\s*(-*\d+\.\d+) degC,\s*(-*\d+\.\d+) degC,\s*(-*\d+.\d+) %RH,\s*(-*\d+\.\d+) degC,\s*(\w+),\s*(\w+),\s*(\w+),\s*(\w+)')
	m = re.match(p,s)
	tset = 0
	hset = 0
	dpset = 0
	tmode = 'N/A'
	hmode = 'N/A'
	vmode = 'N/A'
	bmode = 'N/A'
	if m:
		temp = float(m.group(1))
		hum = float(m.group(2))
		dpnt = float(m.group(3))
		tset = float(m.group(4))
		hset = float(m.group(5))
		dpset = float(m.group(6))
		tmode = m.group(7)
		hmode = m.group(8)
		vmode = m.group(9)
		bmode = m.group(10)
	return(temp,hum,dpnt,tset,hset,dpset,tmode,hmode,vmode,bmode)

# -----------------------------------------------------------------------------
def addStr(s,t):
	if s != "":
		s += ", "
	s += t
	return(s)

# -----------------------------------------------------------------------------
def getMJD():
	mjd = int(time.time()/86400) + 40587
	return(mjd)

# -----------------------------------------------------------------------------
# Data analysis with simple check for data integrity - acceptance limit set by
# caller - this is to prevent data transmission error skewing result. It can 
# provide a bit of a buffer against a rapid change in the parameter
def getAverage(d,lmt):
	mn = statistics.mean(d)
	md = statistics.median(d)
	absdif = abs(mn-md)
	debug(f"Checking data - mean: {mn:.2f} median: {md:.2f} abs diff: "+
			 f"{absdif:.2f}")
	if absdif > lmt:
		return(md)
	return(mn)

# -----------------------------------------------------------------------------
def save_send_data(t,h,dp,sn,t_cor,h_cor,t_set,h_set,dp_set,t_mode,h_mode,
									 v_mode,b_mode):
	temp = getAverage(t,0.05)
	hum = getAverage(h,0.05)
	dpnt = getAverage(dp,0.05)
	
	flnm = datapath+str(getMJD())+'.dat'
	if not(os.path.exists(flnm)):
		with open(flnm,"w") as f:
			f.write('#Environmental sensor data\n')
			f.write('#Set2Yoga\n')
			f.write('#Serial number: {}\n'.format(sn))
			f.write('#            Temperature Humidity Dewpoint Temp_set Hum_set'+
				' DP_set\n')
			f.write('#Time stamp     (degC)     (%RH)   (degC)   (degC)   (%RH)  '+
					 '(degC) Temp_mode Hum_mode Vent_mode Boost_mode\n');
			f.close()
	with open(flnm,"a") as f:
		s = datetime.datetime.utcnow().strftime("%H:%M:%S")
		s += f"{temp:14.2f} {hum:9.2f} {dpnt:8.2f} {t_set:8.2f} {h_set:7.2f} "
		s += f"{dp_set:7.2f} {t_mode:>6s} {h_mode:>8s} {v_mode:>9s} "
		s += f"{b_mode:>9s}\n"
		f.write(s)
		f.close()
		debug('temp = {:0.2f} degC written to {}'.format(temp,flnm))
		debug('hum = {:0.2f} %RH written to {}'.format(hum,flnm))
		debug('dew point = {:0.2f} degC written to {}'.format(dpnt,flnm))
	return(temp,hum,dpnt)

# -----------------------------------------------------------------------------
def saveStatus(statusfile,temp,hum,dp):
	with open(statusfile,'w') as f:
		f.write(f"{temp:0.2f}, {hum:0.2f}, {dp:0.2f}\n")
		f.close()
	debug(f"Data saved in {statusfile}: {temp:0.2f}, {hum:0.2f}, {dp:0.2f}")
	return

# -----------------------------------------------------------------------------
def checktime(tm):
	p = re.compile(r'(\d\d):(\d\d)')
	m = re.match(p,tm.strip())
	retval = True
	if m:
		hr = int(m.groups()[0])
		mn = int(m.groups()[1])
		if hr > 23:
			retval = False
		if mn > 59:
			retval = False
	else:
		retval = False
	return(retval)

# -----------------------------------------------------------------------------
def validVal(v):
	retval = True
	if v > 80:
		retval = False
	return(retval)

# -----------------------------------------------------------------------------
def checkSettingsFile(flnm):
	with open(flnm,"r") as f:
		lines = f.readlines()
		f.close()
		p = re.compile(r'(\w+)\s+(\d\d:\d\d)\s+(\d+.\d+)\s+(\d+.\d+)')
	retval = True
	for line in lines:
		if not line.strip().startswith('#'):
			m = re.match(p,line.strip())
			if m:
				dow = m.groups()[0].upper()
				if not dow in weekdays:
					retval = False
					break
				starttm = m.groups()[1]
				if not checktime(starttm):
					retval = False
					break
				t = float(m.groups()[2])
				if not validVal(t):
					retval = False
					break
				h = float(m.groups()[3])
				if not validVal(h):
					retval = False
					break
	return(retval)

# -----------------------------------------------------------------------------
# Much of this repeats checkSettingsFile but right now I cannot think of a
# better way...
def checkControlFile(flnm):
	now = datetime.datetime.now()
	c_dow = weekdays[now.weekday()]
	c_ts = now.weekday() * 1440 + now.hour * 60 + now.minute
	newcmd = ""
	with open(flnm,"r") as f:
		lines = f.readlines()
		f.close()
		p = re.compile(r'(\w+)\s+(\d\d:\d\d)\s+(\d+.\d+)\s+(\d+.\d+)')
	retval = True
	for line in lines:
		if not line.strip().startswith('#'):
			m = re.match(p,line.strip())
			if m:
				dow = m.groups()[0].upper()
				if not dow in weekdays:
					retval = False
				starttm = m.groups()[1]
				if not checktime(starttm):
					retval = False
				t = float(m.groups()[2])
				if not validVal(t):
					retval = False
				h = float(m.groups()[3])
				if not validVal(h):
					retval = False
				if retval:
					ts = (weekdays.index(dow) * 1440 + int(starttm[0:2])*60 +
						int(starttm[3:5]))
					if c_ts >= ts:
						newcmd = f"SP {t:4.1f} {h:4.1f}"
	debug(f"Command to send (generated from commands file): {newcmd}")
	return(newcmd)

# -----------------------------------------------------------------------------
def sendcmd(cmd):
	debug(f"Command to send: {cmd.strip()}")
	success = False
	cmd = cmd.strip()+'\n'
	while not success:
		ser.write(cmd.encode('ascii'))
		time.sleep(0.2)
		retval = ""
		while ser.in_waiting:
			c = ser.read(1)
			if int.from_bytes(c,byteorder='big',signed=False) >= 32:
				retval = retval + c.decode('ascii')
			else:
				if retval == cmd.strip():
					success = True
			if c == b'\r':
				break
		if success:
			debug(f"Command sent to controller: {cmd.strip()}")
			break
	return

# -----------------------------------------------------------------------------
def savecommandlog(cmd,flnm):
	debug("Saving command to log: {}".format(cmd))
	with open(flnm,"a") as f:
		f.write("{:30s} {}\n".
			format(time.strftime("%Y-%m-%d %A %H:%M:%S",time.localtime()),cmd))
		f.close()
	return

# -----------------------------------------------------------------------------
def getFileTime(flnm):
	if not os.path.isfile(flnm):
		return(0)
	return(os.path.getmtime(flnm))

# -----------------------------------------------------------------------------
def loadSchedule(flnm):
	debug("Reading class schedule from {}".format(flnm))
	schedule = []
	if os.path.isfile(flnm):
		with open(flnm,"r") as f:
			lines = f.readlines()
			f.close()
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
	else:
		errorExit(f"Schedule file ({flnm}) does not exist.")
	debug(f"Schedule read successfully. Found {len(schedule)} classes.")
	return(schedule)

# -----------------------------------------------------------------------------
def readSchedule(sch):
	cday = datetime.datetime.now().strftime('%A').upper()
	hr = int(datetime.datetime.now().strftime('%H'))
	mn = int(datetime.datetime.now().strftime('%M'))
	tm = hr*60+mn
	debug(f"Today is {cday}, and it is now {hr:2d}:{mn:02d}")
	futureClass = 0
	for i in range(0,len(sch)):
		if sch[i][0] == cday:
			hrmn = sch[i][1].split(':')
			sttm = int(hrmn[0])*60+int(hrmn[1])
			#print (tm,sttm)
			if tm < sttm:
				debug(f"Found a future class, starting on {cday} at "+
					f"{hrmn[0]}:{hrmn[1]}")
				futureClass = sttm
				break
	return (futureClass)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Reads data from TFTHP-1 type "+
																 "environment sensor, averages and logs the "+
																 "readings")
parser.add_argument("-v","--version",action="store_true",help="Show version "+
										"and exit.")
parser.add_argument("-c","--config",nargs=1,help="Specify alternative "+
										"configuration file. The default is "+
										"~/etc/temphum.conf.")
parser.add_argument("-s","--settings",nargs=1,help="Specify alternative "+
										"settings file. The default is "+
										"~/etc/temphum.settings.")
parser.add_argument("-l","--log",action="store_true",
										help="Write commands sent to log file.")
parser.add_argument("-d","--debug",action="store_true",
										help="Turn debugging on")

args = parser.parse_args()

if args.log:
	logcommands = True

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

configfile = HOME+"etc/temphum.conf"

if args.config:
	debug(f"Alternate config file specified: {args.config[0]}")
	configfile = str(args.config[0])
	if not configfile.startswith('/'):
		configfile = HOME+configfile

if not os.path.isfile(configfile):
	errorExit(f"{configfile} does not exist.")

debug(f"Configuration file: {configfile}")

conf = configparser.ConfigParser()
conf.read(configfile)

settingsfile = HOME+"etc/temphum.settings"

if args.settings:
	debug(f"Alternate settings file specified: {str(args.settings[0])}")
	settingsfile = str(args.settings[0])
	if not settingsfile.startswith('/'):
		settingsfile = HOME+settingsfile

debug(f"Settings file: {settingsfile}")

if not os.path.isfile(settingsfile):
	errorExit(f"{settingsfile} does not exist.")

if not checkSettingsFile(settingsfile):
	errorExit(f"Issue with {settingsfile}. Check it carefully and try again")

req = ['main,lock file','main,status file','main,logfile',
			 'main,schedule config','comms,port','path,data',
			 'sensor,serial number','sensor,temperature correction',
			 'sensor,humidity correction']

cfg = checkConfig(conf, req)

port = conf['comms']['port']
sn = conf['sensor']['serial number']
try:
	temp_cor = float(conf['sensor']['temperature correction'])
	hum_cor = float(conf['sensor']['humidity correction'])
except:
	errorExit("Something went wrong trying to convert the numbers "+
					  "in the settings file. Please check them carefully.")

# Check if serial device present (it may be a USB device)
if not os.path.exists(port):
	errorExit(f"The serial device {port} does not exist")

# Create UUCP lock for the serial port
uucpLockPath='/var/lock'
if ('paths,uucp lock' in cfg):
	uucpLockPath = conf['paths']['uucp lock']

ret = subprocess.check_output(['/usr/local/bin/lockport','-d',uucpLockPath,
									 '-p',str(os.getpid()),port,sys.argv[0]]).decode('utf-8')

if (re.match('1',ret)==None):
	errorExit('Could not obtain a lock on ' + port + '.')

if logcommands:
	logfile = conf['main']['logfile']
	if not logfile.startswith('/'):
		logfile = HOME+logfile

	debug("Commands log file: {}".format(logfile))

scheduleConfig = conf['main']['schedule config']
if not scheduleConfig.startswith('/'):
	scheduleConfig = HOME+scheduleConfig

if not os.path.isfile(scheduleConfig):
	errorExit(f"Class schedule config file does not exist: {scheduleConfig}")

debug(f"Class schedule config file: {scheduleConfig}")

confSchedule = configparser.ConfigParser()
confSchedule.read(scheduleConfig)

# We only need one setting from the class schedule configuration, so no need
# to check the whole file.

if not confSchedule.has_option('schedule','file'):
	errorExit("Class schedule config file is missing the ['shedule']"+
					 "['file'] option.")

scheduleFile = confSchedule['schedule']['file']
if not scheduleFile.startswith('/'):
	scheduleFile = HOME + scheduleFile

if not os.path.isfile(scheduleFile):
	errorExit(f"Class schedule file does not exist: {scheduleFile}")

debug(f"Class schedule file: {scheduleFile}")

lockfile = conf['main']['lock file']
if not lockfile.startswith('/'):
	lockfile = HOME+lockfile
if not CreateProcessLock(lockfile):
	errorExit(f'Unable to lock - {script} already running?')

debug("Lock file: {}".format(lockfile))

signal.signal(signal.SIGINT,signalHandler)
signal.signal(signal.SIGTERM,signalHandler)
signal.signal(signal.SIGHUP,signalHandler) # not usually run with a
                                           # controlling TTY, but handle it
                                           # anyway

datapath = makePath(conf['path']['data'])
checkPath(datapath)
debug(f"Data will be stored in {datapath}")

statusfile = makeFilePath(conf['main']['status file'])
debug(f"Current temperature / humidity will be stored in {statusfile}")

t = 9999.9
h = 9999.9
dp = 9999.9

tmps = []
hums = []
dewp = []

oldmin = datetime.datetime.utcnow().minute
oldcmd = ""

oldft = 0
classStart = 0
boost_on = False

t_out = 10.0
if ('comms,timeout' in cfg):
	t_out = float(conf['comms']['timeout'])

debug("Serial communications timeout is {:.1f} s.".format(t_out))

debug('Opening '+port)

with serial.Serial(port,115200,timeout = t_out) as ser:
	readtime = time.time()
	while running:
		line = ser.readline()
		if (time.time() - readtime) > t_out:
			print("Error! Serial timeout waiting for data.")
			ser.close()
			break
		readtime = time.time()
		s = line.decode().strip()
		if s != "":
			if s[0] in numbers:
				(t,h,dp,tset,hset,dpset,tm,hm,vm,bm) = getSensorData(s)
				if (t != 9999.9) and (h != 9999.9) and (dp != 9999.9):
					tmps.append(t)
					hums.append(h)
					dewp.append(dp)
					mn = datetime.datetime.utcnow().minute
					if mn != oldmin:
						(t_ave,h_ave,dp_ave) = save_send_data(tmps,hums,dewp,sn,temp_cor,
																						hum_cor,tset,hset,dpset,tm,hm,vm,bm)
						tmps.clear()
						hums.clear()
						dewp.clear()
						oldmin = mn
						saveStatus(statusfile,t_ave,h_ave,dp_ave)
						# Check the settings file to see if new command must be sent to the
						# controller.
						newcmd = checkControlFile(settingsfile)
						if not newcmd == "":
							if not newcmd == oldcmd:
								sendcmd(newcmd)
								if logcommands:
									savecommandlog(newcmd,logfile)
								oldcmd = newcmd
							else:
								debug("Current command is still valid: {}".format(oldcmd))
						# New code (from ver 0.1.6) for booster
						hr = int(datetime.datetime.now().strftime('%H'))
						mn = int(datetime.datetime.now().strftime('%M'))
						# To easily compare times, we count time as minutes from the start
						# of the current day
						tm = hr*60+mn
						ft = getFileTime(scheduleFile)
						if not ft == oldft: # check if class schedule file has changed
							sch = loadSchedule(scheduleFile)
							oldft = ft
						classStart = readSchedule(sch)
						tn = time.strftime('%H:%M',time.localtime())
						clst = (f"{classStart//60:02d}:"+
							f"{classStart - ((classStart//60)*60):02d}")
						debug(f"It is now {tn}; next class starts at: {clst}")
						debug(f"Current temperature: {t_ave:0.2f} degC, setpoint:"+
						f" {tset:0.1f} degC")
						if tm <= classStart:
							if not boost_on:
								if tm + 45 >= classStart:
									debug("45 min check. Check temperature and turn boost on "+
												"if required")
									if tset - t_ave >= 8:
										boost_on = True
										debug(f"Booster on because set temperature "+
													f"({tset:0.1f} degC) is more than "+
													"8 degC higher than actual temperature "+
													f"({t_ave:0.2f} degC) 45 minutes before class.")
								if tm + 30 >= classStart:
									debug("30 min check. Check temperature and turn boost on "+
												"if required")
									if tset - t_ave >= 5:
										boost_on = True
										debug(f"Booster on because set temperature "+
													f"({tset:0.1f} degC) is more than "+
													"5 degC higher than actual temperature "+
													f"({t_ave:0.2f} degC) 30 minutes before class.")
								if tm + 15 >= classStart:
									debug("15 min check. Check temperature and turn boost on "+
												"if required")
									if tset - t_ave >= 2:
										boost_on = True
										debug(f"Booster on because set temperature "+
													f"({tset:0.1f} degC) is more than "+
													"2 degC higher than actual temperature "+
													f"({t_ave:0.2f} degC) 15 minutes before class.")
								if tm + 2 >= classStart:
									debug("2 min check. Check temperature and turn boost on "+
												"if required")
									if tset > t_ave:
										boost_on = True
										debug(f"Booster on because set temperature "+
													f"({tset:0.1f} degC) is more than actual "+
													f"temperature ({t_ave:0.2f} degC) 2 minutes "+
													"before class.")
								if boost_on:
									sendcmd("BOOST ON")
									debug("BOOST is now turned ON")
						if boost_on:
							debug("BOOSTER ON: Checking temperatures. Setpoint: "+
										f"{tset:0.1f} degC, actual value: {t_ave:0.2f} degC.")
							if t_ave >= tset:
								debug(f"Temperature ({t_ave:0.2f} degC) has reached setpoint"+
									f" ({tset:0.1f} degC), turning BOOSTER off.")
								boost_on = False
								sendcmd("BOOST OFF")
								debug("BOOST is now turned OFF")
		time.sleep(0.1)
	ser.close()
	
subprocess.check_output(['/usr/local/bin/lockport','-r',port]) 

RemoveProcessLock(lockfile)

print(f"{ts()} {script} terminated.")
