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
import signal
import subprocess

script = os.path.basename(__file__)
VERSION = "0.1"
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
def signalHandler(signal,frame):
	global running
	running = False
	debug("User / system request for program termination.")
	return

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

parser = argparse.ArgumentParser(description="Checks class schedule, and if it "+
																 "has been modified runs the script that creates "+
																 "the temp hum settings file for control of the "+
																 "hot room")
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

#req = ['checker,lock file','main,settings file','schedule,file']
req = ['checker,lock file','schedule,file','checker,bin file']

cfg = checkConfig(conf, req)

debug("conf['checker']['lock file'] = {}".format(conf['checker']['lock file']))
#debug("conf['main']['settings file'] = {}".format(conf['main']['settings file']))
debug("conf['schedule']['file'] = {}".format(conf['schedule']['file']))
debug("conf['checker']['bin file'] = {}".format(conf['checker']['bin file']))

schflnm = conf['schedule']['file']
if not schflnm.startswith('/'):
	schflnm = HOME + schflnm

debug("Class schedule file: {}".format(schflnm))

if not os.path.isfile(schflnm):
	errorExit('The class schedule file does not exist.')

binfile = conf['checker']['bin file']
if not binfile.endswith('/'):
	binfile = HOME + binfile

debug("Executable to run: {}".format(binfile))

if not os.path.isfile(binfile):
	errorExit("The binary file that you are supposed to run does not exist...")

lockfile = conf['checker']['lock file']

if not lockfile.startswith('/'):
	lockfile = HOME+lockfile

debug("Lock file: {}".format(lockfile))

if not CreateProcessLock(lockfile):
	errorExit('Unable to lock - '+script+' already running?')

signal.signal(signal.SIGINT,signalHandler)
signal.signal(signal.SIGTERM,signalHandler)
signal.signal(signal.SIGHUP,signalHandler) # not usually run with a controlling TTY, but handle it anyway

running = True
fmod_old = 0

while running:
	fmod = os.path.getmtime(schflnm)
	if not fmod == fmod_old:
		#print(fmod)
		fmod_old = fmod
		retval = subprocess.run([binfile],capture_output = True)
		#print(retval)
		if retval.returncode == 0:
			debug("Settings file successfully created")
		else:
			print("Executable: {}".format(binfile))
			print("Return code: {}".format(retval.returncode))
			print("Std out: {}".format(retval.stdout.decode('ascii')))
			print("Std err: {}".format(retval.stderr.decode('ascii')))
			errorExit("Could not create settings file.")
	time.sleep(0.5)
	continue

RemoveProcessLock(lockfile)

debug('{} terminated.'.format(script))
