# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import os, sys, re
from glob import glob
import tempfile
import logging
import numpy as np
import nibabel
from shutil import rmtree
sys.path.insert(0,'/home/jagust/cindeem/CODE/PetProcessing')
import base_gui as bg
import csv
from nipype.interfaces.base import CommandLine
from nipype.utils.filemanip import split_filename, fname_presuffix

def desikan_pibindex_regions():
    """ returns labels form desikan atlas representing regions
    used to determin global pibindex"""
    pibindex = [1003,
               1012,1014,1018,1019,1020,1027,1028,1032,1008,
               1025,1029,1031,1002,1023,1010,1026,2003,
               2012,2014,2018,2019,2020,2027,2028,2032,2008,
               2025,2029,2031,2002,2023,2010,2026,1015,1030,
               2015,2030,2009,1009]
    return pibindex
                                                    
def bbreg_pet_2_mri(subid, pet):
    """bbregister --s B05-216_v1 --mov nonan-ponsnormed_B05-216_v1_fdg.nii
    --init-fsl --reg register.dat --t2"""

    pth, nme, ext = split_filename(pet)
    datfile = os.path.join(pth, '%s_2_FS.dat'%(nme))
    cmd = 'bbregister --s %s --mov %s --init-fsl --reg %s --t2'%(subid,
                                                                 pet,
                                                                 datfile)
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print 'tkregister failed for %s'%(pet)
        print cout.runtime.stderr
        return None
    return datfile


    
def fs_generate_dat(pet, mri, subid):
    """ use freesurfer tkregister to generate a dat file used in
    extracting PET counts with a labelled mri mask in freesurfer

    Parameters
    ----------
    pet : pet file that is registered to the subjects mri

    subdir : subjects freesurfer directory

    Returns
    -------
    dat : dat file generated , or None if fails
    you can check dat with ...
               'tkmedit %s T1.mgz -overlay %s -overlay-reg %s
               -fthresh 0.5 -fmid1'%(subject, pet, dat)
                 
    """
    pth, nme, ext = split_filename(pet)
    xfm = os.path.join(pth, '%s_2_FS.dat'%(nme))
    cmd = 'tkregister2 --mov %s --targ %s --s %s  --regheader --noedit '\
          '--reg %s '%(pet, mri, subid, xfm)

    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print 'tkregister failed for %s'%(pet)
        print cout.runtime.stderr
        return None
    return xfm

def fs_extract_label_rois(subdir, pet, dat, labels):
    """
    Uses freesurfer tools to extract

    Parameters
    -----------
    subdir : subjects freesurfer directory

    pet : filename of subjects PET volume coreg'd to mri space

    dat : filename of dat generated by tkregister mapping pet to mri

    labels : filename of subjects aparc+aseg.mgz

    Returns
    -------
    stats_file: file  that contains roi stats

    label_file : file of volume with label rois in pet space
               you can check dat with ...
               'tkmedit %s T1.mgz -overlay %s -overlay-reg %s
               -fthresh 0.5 -fmid1'%(subject, pet, dat)
                 
    """
    pth, nme, ext = split_filename(pet)
    pth_lbl, nme_lbl, ext_lbl = split_filename(labels)
    
    stats_file = os.path.join(pth, '%s_%s_stats'%(nme, nme_lbl))
    label_file = os.path.join(pth, '%s_%s_.nii.gz'%(nme, nme_lbl))

    # Gen label file
    cmd = ['mri_label2vol',
           '--seg %s/mri/%s'%(subdir, labels),
           '--temp %s'%(pet),
           '--reg'%(dat),
           '--o %s'%(label_file)]
    cmd = ' '.join(cmd)
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print 'mri_label2vol failed for %s'%(pet)
        return None, None
    ## Get stats
    cmd = ['mri_segstats',
           '--seg %s'%(label_file),
           '--sum %s'%(stats_file),
           '--in %s'%(pet),
           '--nonempty --ctab',
           '/usr/local/freesurfer_x86_64-4.5.0/FreeSurferColorLUT.txt']
    cmd = ' '.join(cmd)
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print 'mri_segstats failed for %s'%(pet)
        return None, None
    return stats_file, label_file

    
def parse_fs_statsfile(statsfile):
    """opens a fs generated stats file and returns
    a dict of roi keys with [mean, std, nvox], for
    each roi
    """
    roidict = {}
    for line in open(statsfile):
        if line[0] == '#':
            continue
        tmp = line.split()
        roi = tmp[0]
        mean = eval(tmp[4])
        std = eval(tmp[5])
        nvox = eval(tmp[1])
        roidict.update({roi:[mean, std, nvox]})
    return roidict

def parse_fs_statsfile_vert(statsfile):
    """opens a fs generated stats file and returns
    a dict of roi keys with [mean, std, nvert], for
    each roi
    """
    roidict = {}
    for line in open(statsfile):
        if line[0] == '#':
            continue
        tmp = line.split()
        roi = tmp[0]
        mean = eval(tmp[4])
        std = eval(tmp[5])
        nvox = eval(tmp[1])
        roidict.update({roi:[mean, std, nvox]})
    return roidict



def aseg_label_dict(lut, type='ctx'):
    """ Given a color LUT (look up table)
    return a dict of label : region
    (eg, {17:  'Left-Hippocampus'} )

    Inputs
    ------

    lut : file storing label to region look up table
          /usr/local/freesurfer_x86_64-4.5.0/ASegStatsLUT.txt

    type : string ('ctx', None)
           if ctx, only returns cortex regions
	   else returns all in file

    Returns
    -------

    dict : dictionary mapping label -> region
	   
    """
    outd = {}
    for line in open(lut):
        if '#' in line or 'G_' in line or 'S_' in line:
	    continue
        if type is 'ctx':
            if not type in line:
	        continue
        parts = line.split()
	if len(parts) < 2:
	    continue
        name_as_int = int(parts[0])
        valrange = np.vstack((np.arange(1002, 1036),np.arange(2002, 2036)))
        if type is 'ctx' and name_as_int not in valrange:
            # label is not a cortical label we care about
            continue
        outd[parts[0]] = parts[1]
    return outd
	
def roilabels_fromcsv(infile):
    """ given a csv file with fields
    'pibindex_Ltemporal', '1009', '1015', '1030', '', '', '', '', '', ''
    parses into roi name and array of label values and returns dict"""
    spam = csv.reader(open(infile, 'rb'),
                      delimiter=',', quotechar='"')
    roid = {}
    for item in spam:
        roi = item[0]
        labels = [x for x in item[1:] if not x == '']
        roid[roi] = np.array(labels, dtype=int)
    return roid

def mean_from_labels(roid, labelimg, data, othermask = None):
    meand = {}
    labels = nibabel.load(labelimg).get_data()
    if not labels.shape == data.shape:
        return None
    allmask = np.zeros(labels.shape, dtype=bool)
    for roi, mask in roid.items():
        fullmask = np.zeros(labels.shape, dtype=bool)
        for label_id in mask:
            fullmask = np.logical_or(fullmask, labels == label_id)
            data_mask = np.logical_and(data>0, np.isfinite(data))
            fullmask = np.logical_and(fullmask, data_mask)
            if othermask is not None:
                maskdat = nibabel.load(othermask).get_data()
                fullmask = np.logical_and(fullmask, maskdat > 0)
            # update allmask
            allmask = np.logical_or(allmask, fullmask)
            roimean = data[fullmask].mean()
            roinvox = data[fullmask].shape[0]
            meand[roi] = [roimean, roinvox]
    # get values of all regions
    meand['ALL'] = [data[allmask].mean(), data[allmask].shape[0]]
    return meand

def mean_from_labels_percent(roid, labelimg, data, percent = .50):
    meand = {}
    labels = nibabel.load(labelimg).get_data()
    if not labels.shape == data.shape:
        return None
    allmask = np.zeros(labels.shape, dtype=bool)
    for roi, mask in roid.items():
        fullmask = np.zeros(labels.shape, dtype=bool)
        for label_id in mask:
            fullmask = np.logical_or(fullmask, labels == label_id)
            data_mask = np.logical_and(data>0, np.isfinite(data))
            fullmask = np.logical_and(fullmask, data_mask)
            # update allmask
            allmask = np.logical_or(allmask, fullmask)
            roidat = data[fullmask]
            roidat.sort()
            topindx = int(roidat.shape[0] * percent)
            roimean = roidat[topindx:].mean()
            roinvox = roidat[topindx:].shape[0]
            meand[roi] = [roimean, roinvox]
    # get values of all regions
    meand['ALL'] = [data[allmask].mean(), data[allmask].shape[0]]
    return meand    
    

def meand_to_file(meand, csvfile):
    """given a dict of roi->[mean, nvox]
    unpack to array
    output to file
    """
    fid = open(csvfile, 'w+')
    csv_writer = csv.writer(fid)
    keys = meand.keys()
    tmpd = meand[keys[0]]
    row = ['SUBID',]
    for roinme in sorted(tmpd.keys()):
        row += [roinme, 'std', 'nvox']
    csv_writer.writerow(row)
    for k, tmpd in sorted(meand.items()):
        row = ['%s'%k]
        for roin, (mean, std, nvox) in sorted(tmpd.items()):
            row += ['%f'%mean,'%f'%std,'%d'%nvox]
        csv_writer.writerow(row)
    fid.close()


def pet_2_surf(pet, dat, subjects_dir, proj='projfrac-max'):
    """ uses mri_vol2surf to move pet data into surface space

    eg:
    mri_vol2surf --regheader 009_S_0751 --mov 009_S_0751/pet/ADNI_009_S_0751_FDG_ponsnormd_S18141_I27122.nii
    --reg pet/ADNI_009_S_0751_FDG_ponsnormd_S18141_I27122_2_FS.dat --interp trilinear --hemi lh DEFAULT: projfrac 0.5 or projfrac-max 0 1 0.1
    --sd /home/jagust/connect/data/Normal/freesurfer
    --out lh.fdgponsnormd2.mgh
    """
    petdir, petnme= os.path.split(pet)
    petbase = petnme.split('.')[0]
    subdir, _ = os.path.split(petdir)
    _, subid = os.path.split(subdir)
    cmd = 'mri_vol2surf'
    hemis = ['lh', 'rh']
    outfiles = dict.fromkeys(hemis)
    for hemi in hemis:
        outfile = os.path.join(petdir, hemi+'-'+petbase + '_%s.mgh'%proj)
        if not os.path.isfile(outfile):   
            opts = [ '--regheader %s'%subid,
                     '--mov %s'%pet,
                     '--reg %s'%dat,
                     '--interp trilinear',
                     '--hemi %s'%hemi,
                     '--%s 0 1 0.1'%proj,
                     '--sd %s'%subjects_dir,
                     '--out %s'%outfile]
            fullcmd = cmd + ' ' + ' '.join(opts)
            cout = CommandLine(fullcmd).run()
            if not cout.runtime.returncode == 0:
                print 'mri_vol2surf failed for %s : %s'%(hemi,pet)
                print cout.runtime.stderr
                print cout.runtime.stdout
            else:
                outfiles[hemi] = outfile
        else:
            outfiles[hemi] = outfile
    return outfiles


def generate_aparc_labels(subid, hemi, subjects_dir):
    newlabel_dir = os.path.join(subjects_dir, subid, 'label', 'aparc_labels')
    cmd = ' '.join(['mri_annotation2label',
                    '--subject',
                    subid,
                    '--hemi',
                    hemi,
                    '--outdir',
                    newlabel_dir,
                    '--sd',
                    subjects_dir])
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print cout.runtime.stderr
        return None, cout
    return newlabel_dir, cout


def generate_roilabels(labellist, outlabel):
    cmd = 'mri_mergelabels'
    labels = ' '.join(['-i %s'%x for x in labellist])
    outlabel_str = ' '.join(['-o', outlabel])
    cmd = ' '.join([cmd, labels, outlabel_str])
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print cout.runtime.stderr
        return cout
    return cout    


def rousset_labellist(labeldir, hemi, outdir='rousset_labels'):
    rousset_labels = {'frontal':['frontalpole','lateralorbitofrontal'],
                      'temporal' : ['temporalpole'],
                      'parietal' : ['inferiorparietal'],
                      'precuneus' : ['precuneus'],
                      'cingulate' : ['posteriorcingulate', 'isthmuscingulate']
                      }
    pth, _ = os.path.split(labeldir)
    outdir, exists = utils.make_dir(pth, outdir)
    
    # for each rousset label make or copy
    labelfiles = []
    for label, regions in rousset_labels.items():
        outlabel = os.path.join(outdir, '%s.rousset_%s.label'%(hemi, label))
        tmpregions = [os.path.join(labeldir,
                                   '%s.%s.label'%(hemi, x)) for x in regions]
        if len(regions) == 1:
            utils.copy_file(tmpregions[0], outlabel)
        else:
            generate_roilabels(tmpregions, outlabel)
        labelfiles.append(outlabel)
    return labelfiles

def labels_to_annot(subid, hemi, ctab, annot, labels):
    """ requires proper SUBJECTS_DIR"""
    labels_str = ' '.join(['--l %s'%x for x in labels])
    cmd = ' '.join(['mris_label2annot',
                    '--s',
                    subid,
                    '--h',
                    hemi,
                    '--ctab',
                    ctab,
                    '--a',
                    annot])
    cmd = ' '.join([cmd, labels_str])
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print cout.runtime.stderr
        return None
    else:
        return cout
    

def annot_stats(subid, annot, hemi, subjects_dir):
    """ requires proper SUBJECTS_DIR"""
    cmd = ' '.join(['mris_anatomical_stats',
                    '-a',
                    annot,
                    '-b',
                    subid,
                    hemi])
    
    outf = os.path.join(subjects_dir, subid,
                        'stats', annot.replace('.annot','.stats'))
    if os.path.isfile(outf):
        os.system('rm %s'%outf)
    cmd = ' '.join([cmd, '>> %s'%(outf)])
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print cout.runtime.stderr
        return None
    return outf

def annot_pet_stats(subid, annot, hemi, datafile, subjects_dir):
    """ requires proper SUBJECTS_DIR"""
    cmd = ' '.join(['mris_anatomical_stats',
                    '-a',
                    annot,
                    '-t',
                    datafile,
                    '-b',
                    subid,
                    hemi])
    _, annot_nme = os.path.split(annot)
    outf = os.path.join(subjects_dir, subid,
                        'stats',
                        annot_nme.replace('rois.annot',
                                          'FDG_rois.stats'))
    if os.path.isfile(outf):
        os.system('rm %s'%outf)
    cmd = ' '.join([cmd, '>> %s'%(outf)])
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print cout.runtime.stderr
        return None
    return outf    


def seed_fs(subid, dicom, subjectdir):
    
    cmd = 'recon-all -i %s -sd %s -subjid %s'%(dicom,subjectdir, subid)
    cout = CommandLine(cmd).run()
    if not cout.runtime.returncode == 0:
        print cout.runtime.stderr
        return None
    else:
        return True
