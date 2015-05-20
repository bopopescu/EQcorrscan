#!/usr/bin/python

#------------------------------------------------------------------------------
#   Purpose:    Script to call all elements of EQcorrscan module to search
#               continuous data for likely LFE repeats
#   Author:     Calum John Chamberlain
#------------------------------------------------------------------------------

"""
LFEsearch - Script to generate templates from previously picked LFE's and then
serach for repeats of them in contnuous data.
"""

import sys, os, glob
# sys.path.insert(0,"/home/processor/Desktop/EQcorrscan")


from par import template_gen_par as templatedef
from par import match_filter_par as matchdef
#from par import lagcalc as lagdef
from obspy import UTCDateTime, read as obsread
# First generate the templates
from core import template_gen

if len(sys.argv) == 2:
    flag=str(sys.argv[1])
    if flag == '--debug':
        Test=True
        Prep=False
    elif flag == '--debug-prep':
        Test=False
        Prep=True
    else:
        raise ValueError("I don't recognise the argument, I only know --debug and --debug-prep")
elif len(sys.argv) == 5:
    # Arguments to allow the code to be run in multiple instances
    Split=True
    Test=False
    Prep=False
    args=sys.argv[1:len(sys.argv)]
    for i in xrange(len(args)):
        if args[i] == '--instance':
            instance=int(args[i+1])
            print 'I will run this for instance '+str(instance)
        elif args[i] == '--splits':
            splits=int(args[i+1])
            print 'I will divide the days into '+str(splits)+' chunks'

elif not len(sys.argv) == 1:
    raise ValueError("I only take one argument, no arguments, or two flags with arguments")
else:
    Test=False
    Prep=False
    Split=False

templates=[]
delays=[]
stations=[]
print 'Template generation parameters are:'
print 'sfilebase: '+templatedef.sfilebase
print 'samp_rate: '+str(templatedef.samp_rate)+' Hz'
print 'lowcut: '+str(templatedef.lowcut)+' Hz'
print 'highcut: '+str(templatedef.highcut)+' Hz'
print 'length: '+str(templatedef.length)+' s'
print 'swin: '+templatedef.swin+'\n'
for sfile in templatedef.sfiles:
    print 'Working on: '+sfile+'\r'
    if not os.path.isfile(templatedef.saveloc+'/'+sfile+'_template.ms'):
        template=template_gen.from_contbase(templatedef.sfilebase+'/'+sfile)

        print 'saving template as: '+templatedef.saveloc+'/'+\
                str(template[0].stats.starttime)+'.ms'
        template.write(templatedef.saveloc+'/'+\
                   sfile+'_template.ms',format="MSEED")
    else:
        template=obsread(templatedef.saveloc+'/'+sfile+'_template.ms')
    templates+=[template]
    # Will read in seisan s-file and generate a template from this,
    # returned name will be the template name, used for parsing to the later
    # functions


    # Calculate the delays for each template, do this only once so that we
    # don't have to do it heaps!
    # Check that all templates are the correct length
    for tr in template:
        if not templatedef.samp_rate*templatedef.length == tr.stats.npts:
            raise ValueError('Template for '+tr.stats.station+'.'+\
                             tr.stats.channel+' is not the correct length, recut.'+\
                             ' It is: '+str(tr.stats.npts)+' and should be '+
                             str(templatedef.samp_rate*templatedef.length))
    # Get minimum start time
    mintime=UTCDateTime(3000,1,1,0,0)
    for tr in template:
        if tr.stats.starttime < mintime:
            mintime=tr.stats.starttime
    delay=[]
    # Generate list of delays
    for tr in template:
        delay.append(tr.stats.starttime-mintime)
    delays.append(delay)
    # Generate list of stations in templates
    for tr in template:
        # Correct FOZ channels
        if tr.stats.station=='FOZ':
            tr.stats.channel='HH'+tr.stats.channel[2]
        if len(tr.stats.channel)==3:
            stations.append(tr.stats.station+'.'+tr.stats.channel[0]+\
                            '*'+tr.stats.channel[2]+'.'+tr.stats.network)
            tr.stats.channel=tr.stats.channel[0]+tr.stats.channel[2]
        elif len(tr.stats.channel)==2:
            stations.append(tr.stats.station+'.'+tr.stats.channel[0]+\
                            '*'+tr.stats.channel[1]+'.'+tr.stats.network)
        else:
            raise ValueError('Channels are not named with either three or two charectars')

# Template generation and processing is over, now to the match-filtering

# Sort stations into a unique list - this list will ensure we only read in data
# we need, which is VERY important as I/O is very costly and will eat memory
stations=list(set(stations))

# Now run the match filter routine
from core import match_filter
from obspy import read as obsread
# from obspy.signal.filter import bandpass
# from obspy import Stream, Trace
# import numpy as np
from utils import pre_processing
from joblib import Parallel, delayed

# Loop over days
ndays=int((matchdef.enddate-matchdef.startdate)/86400)+1
newsfiles=[]
f=open('detections/run_start_'+str(UTCDateTime().year)+\
       str(UTCDateTime().month).zfill(2)+\
       str(UTCDateTime().day).zfill(2)+'T'+\
       str(UTCDateTime().hour).zfill(2)+str(UTCDateTime().minute).zfill(2),'w')
f.write('template, detect-time, cccsum, threshold, number of channels\n')
print 'Will loop through '+str(ndays)+' days'
if Split:
    if instance==splits:
        ndays=ndays-(ndays/splits)*(splits-1)
    else:
        ndays=ndays/splits
    print 'This instance will run for '+str(ndays)+' days'
    startdate=matchdef.startdate+(86400*((instance-1)*ndays))
    print 'This instance will run from '+str(startdate)
else:
    startdate=matchdef.startdate
for i in range(0,ndays):
    if 'st' in locals():
        del st


    # Set up where data are going to be read in from
    day=startdate+(i*86400)

    # Read in data using obspy's reading routines, data format will be worked
    # out by the obspy module
    # Note you might have to change this bit to match your naming structure
    actual_stations=[] # List of the actual stations used
    for stachan in stations:
        # station is of the form STA.CHAN, to allow these to be in an odd
        # arrangements we can seperate them
        station=stachan.split('.')[0]
        channel=stachan.split('.')[1]
        netcode=stachan.split('.')[2]
        if not Test:
            # Set up the base directory format
            for base in matchdef.contbase:
                if base[2]==netcode:
                    contbase=base
            if not 'contbase' in locals():
                raise NameError('contbase is not defined for '+netcode)
            baseformat=contbase[1]
            if baseformat=='yyyy/mm/dd':
                daydir=str(day.year)+'/'+str(day.month).zfill(2)+'/'+\
                        str(day.day).zfill(2)
            elif baseformat=='Yyyyy/Rjjj.01':
                daydir='Y'+str(day.year)+'/R'+str(day.julday).zfill(3)+'.01'
            elif baseformat=='yyyymmdd':
                daydir=str(day.year)+str(day.month).zfill(2)+str(day.day).zfill(2)

            # Try and find the appropriate files
            if glob.glob(contbase[0]+'/'+daydir+'/*'+station+'*.'+channel+'.*'):
                if not 'st' in locals():
                    st=obsread(contbase[0]+'/'+daydir+'/*'+station+'*.'+channel+'.*')
                else:
                    st+=obsread(contbase[0]+'/'+daydir+'/*'+station+'*.'+channel+'.*')
                actual_stations.append(station) # Add to this list only if we have the data
            else:
                print 'No data for '+stachan+' for day '+daydir+' in '\
                        +contbase[0]
        else:
            fname='test_data/'+station+'-'+channel+'-'+str(day.year)+\
                           '-'+str(day.month).zfill(2)+\
                           '-'+str(day.day).zfill(2)+'-processed.ms'
            if glob.glob(fname):
                if not 'st' in locals():
                    st=obsread(fname)
                else:
                    st+=obsread(fname)
                actual_stations.append(station)
    actual_stations=list(set(actual_stations))

    if not 'st' in locals():
        print 'No data found for day: '+str(day)
    elif len(actual_stations) < matchdef.minsta:
        print 'Data from fewer than '+str(matchdef.minsta)+' stations found, will not detect'
    else:
        if not Test:
            # Process data
            print 'Processing the data for day '+daydir
            if matchdef.debug >= 4:
                for tr in st:
                    tr=pre_processing.dayproc(tr, templatedef.lowcut, templatedef.highcut,\
                                            templatedef.filter_order, templatedef.samp_rate,\
                                            matchdef.debug, day)
            else:
                st=Parallel(n_jobs=len(st))(delayed(pre_processing.dayproc)(tr, templatedef.lowcut,\
                                                                   templatedef.highcut,\
                                                                   templatedef.filter_order,\
                                                                   templatedef.samp_rate,\
                                                                   matchdef.debug, day)\
                                for tr in st)
        if not Prep:
            # Call the match_filter module - returns detections, a list of detections
            # containted within the detection class with elements, time, template,
            # number of channels used and cross-channel correlation sum.
            print 'Running the detection routine'
            detections=match_filter.match_filter(templatedef.sfiles, templates, delays, st,
                                                 matchdef.threshold, matchdef.threshtype,
                                                 matchdef.trig_int,  matchdef.plot)

            for detection in detections:
                # output detections to file
                f.write(detection.template_name+', '+str(detection.detect_time)+\
                        ', '+str(detection.detect_val)+', '+str(detection.threshold)+\
                        ', '+str(detection.no_chans)+'\n')
                print 'template: '+detection.template_name+' detection at: '\
                    +str(detection.detect_time)+' with a cccsum of: '+str(detection.detect_val)
            if detections:
                f.write('\n')
        else:
            for tr in st:
                tr.write('test_data/'+tr.stats.station+'-'+tr.stats.channel+\
                         '-'+str(tr.stats.starttime.year)+\
                         '-'+str(tr.stats.starttime.month).zfill(2)+\
                         '-'+str(tr.stats.starttime.day).zfill(2)+\
                         '-processed.ms', format='MSEED')
f.close()
