# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import sys, os
import nibabel.ecat as ecat
import dicom
import numpy as np
from datetime import datetime
import csv
from glob import glob
import pandas

def get_series_iter(infile):
    """ based on structure of current dicoms
    returns iterator for files to junm between
    frames"""
    plan = dicom.read_file(infile)
    ns = plan.NumberOfSlices
    nts = plan.NumberOfTimeSlices
    ii = plan.ImageIndex
    return np.arange(0,nts*ns, ns)


def sort_series(infiles):
    nfiles = len(infiles)
    out = np.recarray((nfiles), dtype=[('x', int), ('file', 'S250')])
    for val, f in enumerate(infiles):
        plan = dicom.read_file(f)
        ii = plan.ImageIndex
        out.x[val] = ii
        out.file[val] = f
    sort_mask = out.argsort(axis=0)    
    out = out[sort_mask]# sort to correct order
    return out


def frametime_from_dicoms(infiles):
    """ given a dicom series,
    find timing info for each frame
    """
    frametimes = []
    files = []
    sorted = sort_series(infiles)
    fiter = get_series_iter(infiles[0])
    for f in sorted.file[fiter]:
        plan = dicom.read_file(f)
        st = datetime.fromtimestamp(float(plan.StudyTime))
        at = datetime.fromtimestamp(float(plan.AcquisitionTime))
        dur = float(plan.ActualFrameDuration)
        start = (at -st).microseconds * 1000
        frt = datetime.fromtimestamp(float(plan.FrameReferenceTime))
        end = start + dur
        frametimes.append([frt.microsecond * 1000, at.microsecond * 1000, dur, st.microsecond * 1000])
        files.append(f)
    return frametimes, files
        

        
def frametime_from_ecat(ecatf):
    """given an ecat file , finds timing info for each frame
    
    Returns
    -------
    out : array
          array holding framenumber, starttime, endtime, duration
          in milliseconds
    """
    img = ecat.load(ecatf)
    shdrs = img.get_subheaders()
    mlist = img.get_mlist()
    framenumbers = mlist.get_series_framenumbers()
    out = np.zeros((len(framenumbers), 4))
    if shdrs.subheaders[0]['frame_start_time']== 16:
        adj = 16
    else:
        adj = 0
    for i, fn in framenumbers.items():
        startt = shdrs.subheaders[i]['frame_start_time']
        dur = shdrs.subheaders[i]['frame_duration']
        out[i,0] = fn 
        out[i,1] = startt - adj
        # fix adj, divide by 60000 to get minutes
        out[i,3] = dur
        out[i,2] = startt - adj + dur
    out = out[out[:,0].argsort(),]
    return out


def frametimes_from_ecats(filelist):
    """
    for each ecat file in filelist
    gets the frame number, start, duration info
    combines
    sorts and retruns

    Returns
    -------
    out : array
          array holding framenumber, starttime, endtime, duration
          in milliseconds
          
    """
    if not hasattr(filelist, '__iter__'):
        filelist = [filelist]
    for f in filelist:
        tmp = frametime_from_ecat(f)
        try:
            out = np.vstack((out, tmp))
        except:
            out = tmp
    out = out[out[:,0].argsort(),]
    return out


def frametimes_to_seconds(frametimes, type = 'sec'):
    """ assumes a frametimes array
    type = 'sec', or 'min'
    [frame, start, duration, stop]
    converts to type (default sec (seconds))
    """
    
    newframetimes = frametimes.copy()
    newframetimes[:,1:] = frametimes[:,1:] / 1000.
    if type == 'min':
        newframetimes[:,1:] = newframetimes[:,1:]  / 60.
    return newframetimes




def make_outfile(infile, name = 'frametimes'):
    pth, _ = os.path.split(infile)
    newname = name + datetime.now().strftime('-%Y-%m-%d_%H-%M') + '.csv'
    newfile = os.path.join(pth, newname)
    return newfile

def write_frametimes(inarray, outfile):
    csv_writer = csv.writer(open(outfile, 'w+'))
    csv_writer.writerow(['frame', 'start','stop', 'duration'])
    for row in inarray:
        csv_writer.writerow(row)

def read_frametimes(infile):
    dat = pandas.read_csv(infile)
    outarray = dat.values
    rows, cols = outarray.shape
    if cols < 4:
        dat =  pandas.read_csv(infile, sep=None)# guess correct sep
        outarray = dat.values
        rows, cols = outarray.shape
        if cols < 4:
            raise IOError('CSV not parsing properly, check file')
    # sort by frame
    outarray = outarray[outarray[:,0].argsort(),]
    return outarray




   
