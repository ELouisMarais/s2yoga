#!/usr/bin/python3
# createTempHum.py

# A script to create an image with the current temperatures and humidities
# in the studio.
#
#


# -----------------------------------------------------------------------------
# Ver: 1.0
# Author: Louis Marais
# Start: 2025-04-21
# Last: 2025-??-??
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
import signal
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.dates import DateFormatter

script = os.path.basename(__file__)
VERSION = "1.0"
AUTHORS = "Louis Marais"

DEBUG = False

# -----------------------------------------------------------------------------
# Subroutines
# -----------------------------------------------------------------------------

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
def checkPath(p):
	if not os.path.isdir(p):
		errorExit('The path '+p+' does not exist')
	return

# -----------------------------------------------------------------------------
def makePath(s):
	if not s.startswith(os.sep):
		s = HOME + s
	if not s.endswith(os.sep):
		s = s + os.sep
	return(s)

# -----------------------------------------------------------------------------
def makeFilename(fl):
	if not fl.startswith(os.sep):
		fl = HOME + fl
	return(fl)

# -----------------------------------------------------------------------------
def signalHandler(signal,frame):
	global running
	running = False
	return

# -----------------------------------------------------------------------------
def checktimestamp(t):
	retval = True
	p = re.compile(r'(\d{4})-(\d{2})-(\d{2})\s(\d{2}):(\d{2})')
	m = re.match(p,t)
	if m:
		#print(m.groups())
		debug("checktimestamp: Valid string supplied")
		yr = int(m.groups()[0])
		mn = int(m.groups()[1])
		dy = int(m.groups()[2])
		hh = int(m.groups()[3])
		mm = int(m.groups()[4])
		#print(yr,mn,dy,hh,mm)
		try:
			dto = datetime.datetime(yr,mn,dy,hh,mm)
		except:
			debug(f"checktimestamp: Supplied timestamp is invalid: {t}")
			return False
		# dto is VALID, check that it is in the past
		tm = time.mktime(dto.timetuple())
		now = time.time()
		if now < tm:
			debug("checktimestamp: Specified time is in the future!")
			retval = False
		#tobj = time.mktime(tt)
		#
		#print(tobj)
	return retval

# -----------------------------------------------------------------------------
def getMJD(t):
	mjd = t/86400 + 40587
	return(mjd)

# -----------------------------------------------------------------------------
def gettimelimits(t,d):
	p = re.compile(r'(\d{4})-(\d{2})-(\d{2})\s(\d{2}):(\d{2})')
	m = re.match(p,t)
	if m:
		#print(m.groups())
		debug("checktimestamp: Valid string supplied")
		yr = int(m.groups()[0])
		mn = int(m.groups()[1])
		dy = int(m.groups()[2])
		hh = int(m.groups()[3])
		mm = int(m.groups()[4])
	else:
		errorExit("checktimestamp: This should not be happening....")
	dto = datetime.datetime(yr,mn,dy,hh,mm)  # local time
	#debug(f"dto: {dto}")
	ltm = time.mktime(dto.timetuple())       # UTC time (??? it is I promise!)
	#debug(f"ltm: {ltm}")
	#tm = time.mktime(time.gmtime(ltm))       # UTC time
	#debug(f" tm: {tm}")
	startMJD = getMJD(ltm)
	endMJD = getMJD(ltm + d*3600)
	return(startMJD,endMJD)

# -----------------------------------------------------------------------------
def createimage(flnm,pth,ext,strT,dur,wdth,hght):
	# Find start and end times
	startt,endt = gettimelimits(strT,dur)
	debug(f"createimage: Plot starts at {strT}, and is {dur} hour(s) long")
	debug(f"createimage: This is from MJD {startt:0.5f} to MJD {endt:0.5f}")
	# Find files to read
	mjds = []
	flnms = []
	for i in range(int(startt),int(endt)+1):
		fl = f"{pth}{i}.{ext}"
		if os.path.isfile(fl):
			mjds.append(i)
			flnms.append(fl)
			debug(f"createimage: File '{flnms[-1]}' added.")
		else:
			debug(f"createimage: Oops! {fl} does not exist!")
	if len(flnms) == 0:
		debug("No files available for creating a graph.")
		return
	# Read data
	x = []
	t = []
	h = []
	p = re.compile(r'(\d{2}):(\d{2}):(\d{2})\s+(\d+\.\d+)\s+(\d+\.\d+)\s+')
	for i in range(0,len(flnms)):
		lines = []
		with open(flnms[i],'r') as f:
			lines = f.readlines()
			f.close()
		#print(flnms[i],len(lines))
		for l in lines:
			if l.startswith('#'):
				continue
			m = re.match(p,l)
			if m:
				#print(m.groups())
				hr = int(m.groups()[0])
				mn = int(m.groups()[1])
				sc = int(m.groups()[2])
				ts = mjds[i] + ((hr * 3600 + mn * 60 + sc)/86400)
				#print(ts)
				if ts >= startt and ts <= endt:
					x.append(ts)
					t.append(float(m.groups()[3]))
					h.append(float(m.groups()[4]))
					#print(l.strip())
					#print(x[-1],t[-1],h[-1])
	# Create image
	debug(f"createimage: Found {len(x)} data points.")

	# Test matplotlib
	#x = [1,2,3,4,5,6,7,8,9,10]
	#y = [1,0,1,0,1,0,1,0,1,0]

	xLbls = [time.strftime('%Y-%m-%d %H:%M',time.localtime((t-40587)*86400+0.5))
					for t in x]
	#print(xLbls)

	fig,ax1 = plt.subplots(figsize = (12,7))
	ax2 = ax1.twinx()
	ax1.set_ylim(20,50)
	ax2.set_ylim(30,60)
	#ax1.set_xlabel("Date and time",fontsize=14,fontweight="bold")
	ax1.tick_params(axis='x',labelcolor='black',labelsize=10,labelrotation = 15)
	ax1.set_ylabel("Temperature (\N{DEGREE SIGN}C)",color='red',fontsize=14,
								fontweight='bold')
	ax1.tick_params(axis='y',labelcolor='red',labelsize=14)
	ax2.set_ylabel("Humidity (%RH)",color='blue',fontsize=14,fontweight='bold')
	ax2.tick_params(axis='y',labelcolor='blue',labelsize=14)

	#ax1.plot(x,t,color = 'red')
	#ax2.plot(x,h,color = 'blue')
	#ax1.plot(xLbls,t,color = 'red')
	#ax2.plot(xLbls,h,color = 'blue')
	plt.title("S2Yoga hot room",fontsize=20,fontweight='bold')
	ax1.grid(axis='both',linestyle='--')

	#xstr = 0
	#xstp = len(xLbls)
	#xstep = len(xLbls)/6
	#ax1.xaxis.set_ticks(np.arange(xstr,xstp,xstep))

	xvals = np.array(xLbls,dtype='datetime64')
	tvals = np.array(t)
	hvals = np.array(h)

	date_fmt = DateFormatter("%Y-%m-%d %H:%M")
	ax1.xaxis.set_major_formatter(date_fmt)

	ax1.plot(xvals,tvals,color='red',lw=3)
	ax2.plot(xvals,hvals,color='blue')

	plt.savefig(flnm)
	#plt.show()

	debug(f"createimage: New image created. Saved to {flnm}")
	return

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

HOME = makePath(os.path.expanduser('~'))

etcpath = f"{HOME}etc{os.sep}"

parser = argparse.ArgumentParser(description="Generate an image file with "+
																 "studio temperature and humidity.")
parser.add_argument("-v","--version",action="store_true",help="Show "+
																 "version and exit.")
parser.add_argument("-c","--config",nargs=1,help="Specify alternative "+
																 "configuration file. The default is "+
																 f"{etcpath}showtemphum.conf.")
parser.add_argument("-d","--debug",action="store_true",
																 help="Turn debugging on")
parser.add_argument("-s","--starttime",nargs=1,help="Specify the date and "+
										"time when the plot must start as a string in format "+
										"'YYYY-MM-DD HH:MM'. Default is current date "+
										"time minus duration (default duration is 3 hours).")
parser.add_argument("-t","--duration",nargs=1,help="Duration of the graph in "+
										"hours. Default is 3 hours. This overrides the value in "+
										"the configuration file.")
parser.add_argument("-r","--runonce",action="store_true",help="Create a "+
										"single plot and exit. This option is automatically "+
										"set if the '--starttime' option is invoked.")
args = parser.parse_args()

if args.debug:
	DEBUG = True

versionStr = script+" version "+VERSION+" written by "+AUTHORS

if args.version:
	print(versionStr)
	sys.exit(0)

debug(f"Current user's home: {HOME}")

debug(versionStr)
configfile = f"{etcpath}showtemphum.conf"

if args.config:
	debug(f"Alternate config file specified: {str(args.config[0])}")
	configfile = makeFilename(str(args.config[0])) # Won't work in Windows!

debug(f"Configuration file: {configfile}")

if args.version:
	print(versionStr)
	sys.exit(0)

debug(versionStr)

conf = configparser.ConfigParser()
conf.read(configfile)

req = ['paths,data files','paths,extension','paths,lock file','paths,image',
			 'create,interval','create,duration','create,width','create,height']

cfg = checkConfig(conf, req)

datapath = makePath(conf['paths']['data files'])
filext = conf['paths']['extension']
lockfile = makeFilename(conf['paths']['lock file'])
imagefile = makeFilename(conf['paths']['image'])
try:
	createinterval = int(conf['create']['interval'])
except:
	errorExit("INT conversion error in conf['create']['interval']: "+
			 f"{conf['create']['interval']}")

duration = conf['create']['duration']
debug(f"Graph duration specified in configuration: {conf['create']['duration']} hour(s)")
if args.duration:
	debug(f"User specified custom duration on the command line: {args.duration[0]} hour(s)")
	duration = args.duration[0]

try:
	plotduration = float(duration)
except:
	errorExit("FLOAT conversion error in duration: "+
			 f"{duration}")
try:
	imgwidth = int(conf['create']['width'])
except:
	errorExit("INT conversion error in conf['create']['width']: "+
			 f"{conf['create']['width']}")
try:
	imgheight = int(conf['create']['height'])
except:
	errorExit("INT conversion error in conf['create']['height']: "+
			 f"{conf['create']['height']}")

checkPath(datapath)
debug(f"Data path: {datapath}")
checkPath(os.path.dirname(lockfile))
debug(f"Lock file: {lockfile}")
debug(f"Image filename (to be created): {imagefile}")
debug(f"An image file will be created every {createinterval} minute(s)")
debug(f"Duration of graph will be {plotduration:0.1f} hour(s)")
debug(f"The image will be {imgwidth} x {imgheight} pixels in size.")

starttime = time.strftime("%Y-%m-%d %H:%M",time.localtime(time.time() -
																						plotduration*3600))
debug(f"Default start time (now!) for graph: {starttime}")

if args.starttime:
	st = args.starttime[0]
	if not checktimestamp(st):
		errorExit(f"Invalid start time specified on command line: {args.starttime[0]}")
	starttime = st
	args.runonce = True

if not args.runonce:
	if not CreateProcessLock(lockfile):
		errorExit('Unable to lock - '+script+' already running?')

signal.signal(signal.SIGINT,signalHandler)
signal.signal(signal.SIGTERM,signalHandler)
signal.signal(signal.SIGHUP,signalHandler) # not usually run with a
                                           # controlling TTY, but handle it
                                           # anyway

running = True

# Ensure that an image is created when the loop is entered.
lastimage = time.time() - 1

while running:
	if time.time() > lastimage:
		if not args.starttime:
			starttime = time.strftime("%Y-%m-%d %H:%M",time.localtime(time.time() -
																						plotduration*3600))
		createimage(imagefile,datapath,filext,starttime,plotduration,imgwidth,
							imgheight)
		lastimage += createinterval * 60
	time.sleep(0.1)
	if args.runonce:
		debug("The '--runonce' option is active. Exiting now.")
		break

if not args.runonce:
	RemoveProcessLock(lockfile)

debug(f"{script} done.")
