#!/usr/bin/python3
# sgp30log.py

# Logging the values of an air quality sensor, with eCO2 used as the metric
# Baseline is 400 ppm.
# Send humidity and temperature values to sensor at regular intervals to
# improve measurements.

# From https://wiki.dfrobot.com/SKU_SEN0514_Gravity_ENS160_Air_Quality_Sensor
#
# For a different sensor but still valid:
#
#  (ppm)
# eCO2/CO2     Level          Suggestion
# ~~~~~~~~~  ~~~~~~~~~~  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   21500+    Terrible   Indoor air pollution is serious and requires ventilation
# 1000-1500     Bad      Indoor air is polluted, ventilation is recommended
#  800-1000  Generally   Can be ventilated
#  600-800     Good      Keep it normal
#  400-600   Excellent   No suggestion
#

# -----------------------------------------------------------------------------
# Version: 0.1
# Author: Louis Marais
# Start date: 2023-07-14
# Last modifications: 2023-07-16
#
# Modifications:
# ~~~~~~~~~~~~~~
# Initial version
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
import sys
import argparse
import configparser
import subprocess
import signal
import serial
import time
import datetime
import re
import statistics

script = os.path.basename(__file__)
VERSION = "0.1"
AUTHORS = "Louis Marais"

DEBUG = False

# -----------------------------------------------------------------------------
# Sub routines
# -----------------------------------------------------------------------------
def signalHandler(signal,frame):
	global running
	running = False
	debug("User / system request for program termination.")
	return

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
def getMJD():
	mjd = int(time.time()/86400) + 40587
	return(mjd)

# -----------------------------------------------------------------------------
def savedata(datapath,eco2s,sn,statusfile):
	eco2 = statistics.mean(eco2s)
	debug("Mean (previous minute) eCO2: {:0.1f} ppm".format(eco2))
	flnm = datapath+str(getMJD())+'.dat'
	if not(os.path.exists(flnm)):
		with open(flnm,'w') as f:
			f.write('# SGP30 VOC eCO2 sensor data\n')
			f.write("# Set2yoga\n")
			f.write("# Model: Adafruit SGP30 Air Quality\n")
			f.write("# Serial number: {}\n".format(sn))
			f.write('#               eCO2\n')
			f.write('#Time stamp     (ppm)\n');
			f.close()
	with open(flnm,"a") as f:
		s = datetime.datetime.utcnow().strftime("%H:%M:%S")
		s += " {:14.1f}\n".format(eco2)
		f.write(s)
		f.close()
	with open(statusfile,"w") as f:
		f.write("{:0.1f}\n".format(eco2))
		f.close()
	return

# -----------------------------------------------------------------------------
def getTempHum(flnm):
	# Defaults
	temp = 23
	hum = 50
	if os.path.isfile(flnm):
		with open(flnm,'r') as f:
			s = f.readline()
			f.close()
		debug("Read {} from {}".format(s.strip(),flnm))
		d = s.split(',')
		try:
			tval = float(d[0].strip())
			hval = float(d[1].strip())
			debug("Temperature: {:0.2f} degC, Humidity: {:0.2f} %RH".
				 format(tval,hval))
		except:
			return(temp,hum)
		return(tval,hval)
	else:
		debug("File ({}) not found".format(flnm))
	return(temp,hum)

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Reads data from SGP30 "+
																 "air quality sensor, averages and logs the "+
																 "eCO2 readings")
parser.add_argument("-v","--version",action="store_true",help="Show version "+
										"and exit.")
parser.add_argument("-c","--config",nargs=1,help="Specify alternative "+
										"configuration file. The default is "+
										"~/etc/sgp30.conf.")
parser.add_argument("-d","--debug",action="store_true",help="Turn debugging on")

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

configfile = HOME+"etc/sgp30.conf"

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

req = ['main,lock file','main,temphum file','main,status file','comms,port',
			 'path,data']

cfg = checkConfig(conf, req)

port = conf['comms']['port']
statusfile = makeFilePath(conf['main']['status file'])
debug("Equivalent CO2 values will be stored in {}".format(statusfile))

# Create UUCP lock for the serial port
uucpLockPath='/var/lock'
if ('paths,uucp lock' in cfg):
	uucpLockPath = conf['paths']['uucp lock']

ret = subprocess.check_output(['/usr/local/bin/lockport','-d',uucpLockPath,
									 '-p',str(os.getpid()),port,sys.argv[0]]).decode('utf-8')

if (re.match('1',ret)==None):
	errorExit('Could not obtain a lock on ' + port + '.')

lockfile = conf['main']['lock file']
if not lockfile.startswith('/'):
	lockfile = HOME+lockfile
if not CreateProcessLock(lockfile):
	errorExit('Unable to lock - '+script+' already running?')

signal.signal(signal.SIGINT,signalHandler)
signal.signal(signal.SIGTERM,signalHandler)
signal.signal(signal.SIGHUP,signalHandler) # not usually run with a controlling TTY, but handle it anyway

datapath = makePath(conf['path']['data'])
checkPath(datapath)
debug("Data will be stored in {}".format(datapath))

temphumfile = makeFilePath(conf['main']['temphum file'])
debug("Current temperature / humidity can be found in {}".format(temphumfile))

t_out = 10.0
if ('comms,timeout' in cfg):
	t_out = float(conf['comms']['timeout'])

debug("Serial communications timeout is {:.1f} s.".format(t_out))

debug('Opening '+port)

ser = serial.Serial(port,115200,timeout = t_out);
#
# Opening the serial port resets the Arduino Nano, but not the Leonardo...
# Wait for sensor to communicate; the Arduino will send:
#
#    SGP30 sensor
#    Found SGP30 serial #017E3A8B
#
# and then start to send eCO2 values in PPM approx every second:
#    400
#    etc.
#

s = ""
foundSN = False
sn = ""
startT = time.time()
t_out = False
running = True

debug("Waiting for SGP30 device serial number...")

while True:
	while ser.in_waiting > 0:
		c = ser.read(1)
		if c[0] >= 32:
			s += c.decode('utf-8')
		if c[0] == 10:
			p = re.compile(r'Found SGP30 serial #(.*)') # SGP30 serial #(\.+)')
			m = re.match(p,s)
			if m:
				sn = m.groups()[0]
				debug("Serial number: {}".format(sn))
				foundSN = True
				break
			s = ""
		time.sleep(0.05)
		if not running:
			break
	if foundSN:
		ser.write(bytes('OK\r\n','utf-8'))
		time.sleep(0.5)
		ser.write(bytes('OK\r\n','utf-8'))
		break
	if time.time() > startT + 120.0:  # Two minutes is enough...
		t_out = True
		time.sleep(0.1) # To stop CPU going nuts.
	if not running:
		t_out = True
		break

s = ""

now = time.time()
updateTH = now
update_interval = 60  # seconds

eco2s = []

oldmin = datetime.datetime.utcnow().minute

while running and not t_out:
	while ser.in_waiting > 0:
		c = ser.read(1)
		if c[0] >= 32:
			s += c.decode('utf-8')
		if c[0] == 10:
			p = re.compile(r'(\d+)')
			if re.match(p,s):
				debug("eCO2 = {} ppm".format(s))
				eco2s.append(float(s))
				mn = datetime.datetime.utcnow().minute
				if mn != oldmin:
					savedata(datapath,eco2s,sn,statusfile)
					eco2s.clear()
					oldmin = mn
			else:
				p = re.compile(r'Found SGP30 serial #(.*)') # SGP30 serial #(\.+)')
				m = re.match(p,s)
				if not m:
					debug("Unknown data received: {}".format(s))
				else:
					debug("Serial number received: {}".format(m.groups()[0]))
			s = ""
	time.sleep(0.1) # prevents CPU from going nuts.
	
	if time.time() > updateTH:
		(temp,hum) = getTempHum(temphumfile)
		msg = "{:0.2f}, {:0.2f}\n\r".format(temp,hum)
		ser.write(bytes(msg,'utf-8'))
		debug("Sent temperature and humidity to sensor: {:0.2f} degC, {:0.2f} %RH".
				format(temp,hum))
		updateTH = updateTH + update_interval
	

if t_out:
	print("SGP30 sensor could not be found.")

ser.close()

subprocess.check_output(['/usr/local/bin/lockport','-r',port]) 

RemoveProcessLock(lockfile)

print(ts(),script,'terminated.')


