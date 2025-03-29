#!/usr/bin/python3
# upload.py

# A script to upload IoT data to Adafruit
#
# Read file for temp / hum and file for eCO2 and upload data to Adafruit.
#
# -----------------------------------------------------------------------------
# Ver: 0.0.1
# Author: Louis Marais
# Start: 2023-12-23
# Last: 2023-12-24
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
# -----------------------------------------------------------------------------

import os
import sys
import time
import argparse
import configparser
import signal
from Adafruit_IO import Client, Feed

script = os.path.basename(__file__)
VERSION = "0.0.1"
AUTHORS = "Louis Marais"

DEBUG = False

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
def send_data(conf,thflnm,eco2flnm):
	try:
		key = conf['adafruit']['key']
		user = conf['adafruit']['user']
		aio = Client(user, key)
		if os.path.isfile(thflnm):
			with open(thflnm,"r") as f:
				s = f.readline()
				f.close()
			try:
				l = list(filter(None,s.strip().split(',')))
				if len(l) == 3:
					temp = float(l[0])
					aio.send_data("studio-temp",temp)
					#aio.send_data("home-temp",temp)
					debug("Temperature sent to Adafruit: {:0.1f}".format(temp))
					hum = float(l[1])
					aio.send_data("studio-hum",hum)
					#aio.send_data("home-hum",hum)
					debug("Humidity sent to Adafruit: {:0.1f}".format(hum))
					dpnt = float(l[2])
					aio.send_data("studio-dewpoint",dpnt)
					#aio.send_data("home-dewpoint",dpnt)
					debug("Dewpoint sent to Adafruit: {:0.1f}".format(dpnt))
			except:
				pass
		if os.path.isfile(eco2flnm):
			with open(eco2flnm,"r") as f:
				s = f.readline()
				f.close()
			try:
				eco2 = float(s.strip())
				aio.send_data("studio-eco2",eco2)
				#aio.send_data("home-eco2",eco2)
				debug("eCO2 value sent to Adafruit dashboard: {:0.1f} ppm".
				 format(eco2))
			except:
				pass
	except:
		debug('Data NOT sent to Adafruit dashboard - check connection')
	return

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Reads data from status files "+
																 "for environment sensors, and uploads the "+
																 "data to the Adafruit IoT portal.")
parser.add_argument("-v","--version",action="store_true",help="Show version "+
										"and exit.")
parser.add_argument("-c","--config",nargs=1,help="Specify alternative "+
										"configuration file. The default is "+
										"~/etc/upload.conf.")
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

configfile = HOME+"etc/upload.conf"

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

req = ['main,lock file','main,thfile','main,eco2file',
			 'adafruit,user','adafruit,key']

cfg = checkConfig(conf, req)

debug("Configuration: conf['main']['lock file'] = {}".
			format(conf['main']['lock file']))
debug("Configuration: conf['main']['thfile']    = {}".
			format(conf['main']['thfile']))
debug("Configuration: conf['main']['eco2file']  = {}".
			format(conf['main']['eco2file']))
debug("Configuration: conf['adafruit']['user']  = {}".
			format(conf['adafruit']['user']))
debug("Configuration: conf['adafruit']['key']   = {}".
			format(conf['adafruit']['key']))

lockfile = conf['main']['lock file']

if not lockfile.startswith('/'):
	lockfile = HOME+lockfile

debug("Lock file: "+lockfile)

thfile = conf['main']['thfile']

if not thfile.startswith('/'):
	thfile = HOME+thfile

debug("Temperature, humidity and dew point status file: "+thfile)

eco2file = conf['main']['eco2file']

if not eco2file.startswith('/'):
	eco2file = HOME+eco2file

debug("eCO2 status file: "+eco2file)

if not CreateProcessLock(lockfile):
	errorExit('Unable to lock - '+script+' already running?')

signal.signal(signal.SIGINT,signalHandler)
signal.signal(signal.SIGTERM,signalHandler)
signal.signal(signal.SIGHUP,signalHandler) # not usually run with a
                                           # controlling TTY, but handle it
                                           # anyway

running = True

oldmn = -1

while running:  # Loop forever
	now = time.localtime()
	mn = int(time.strftime("%M",now))
	if mn != oldmn:
		time.sleep(0.2)
		oldmn = mn
		time.sleep(0.2)
		send_data(conf,thfile,eco2file)
	time.sleep(0.5)

RemoveProcessLock(lockfile)

print(ts(),script,'terminated.')

