# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """sets up subject directory structure
    Select subs from ARDA,
    1. creates output dirs
    2. copies pet data to Raw
    3. converts
    """

    # start wx gui app
    app = wx.App()

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose project data dir',
                              indir = '/home/jagust')

    mridir = bg.SimpleDirDialog(prompt='Choose Freesurfer data dir',
                                indir = '/home/jagust')
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(root,'logs',
                           '%s_%s.log'%(__file__,cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)

    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START Setup Directory :::')
    logging.info('###TRACER Setup %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    logging.info('%s'%__file__)
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%mridir)
    
    alldirs = []

    for s in subs:
        _, subid = os.path.split(s)
        globstr = '%s/%s/%s*'%(arda,subid,tracer)
        
        dirs = glob(globstr)
        alldirs.extend(dirs)
    
    finalchoice = bg.MyScanChoices(alldirs)
    #global outdict
    outdict = {}
    bg.make_subject_dict(finalchoice,outdict) 
    
    for item in sorted(outdict):
        if 'None' in outdict[item][0]:
            #print 'skipping %s'%(item)
            logging.info('skipping %s' %(item))
            continue
        else:
            petdir = outdict[item][0]
        subid, _ = os.path.split(item)
        print subid
        logging.info(subid)
        ### XXXXXXXXXXXXXXXXX
        ##  set_up_dir
        outdirs = pp.set_up_dir(root, subid, tracer)

        ## set up MRI
        brainmask = os.path.join(outdirs['anatomydir'][0],
                                 'brainmask.nii')
        fsmri = pp.find_single_file(os.path.join(mridir,
                                                 subid,
                                                 'mri/brainmask.mgz'))
        if os.path.isfile(brainmask):
            logging.warning('%s has existing anatomy,'\
                            'skipping'%(brainmask))
        elif fsmri is None:
            logging.error('NO MRI: %s'%(fsmri)) 
            
        else:
            fsmri = bg.copy_file(fsmri, outdirs['anatomydir'][0])
            brainmask = bg.convert(fsmri, brainmask)
            bg.remove_files([fsmri])
            # copy aseg+aparc
        aparcnii = os.path.join(outdirs['anatomydir'][0],
                                '%s_aparc_aseg.nii.gz'%subid) 
        aparc = pp.find_single_file(os.path.join(mridir,
                                                 subid,
                                                 'mri/aparc+aseg.mgz'))
        if os.path.isfile(aparcnii):
            logging.warning('%s has existing anatomy,'\
                            'skipping'%(aparcnii))
        elif aparc is None:
            logging.error('NO APARC ASEG: %s'%aparc)

        else:
            aparc = bg.copy_file(aparc, outdirs['anatomydir'][0])
            aparcnii = bg.convert(aparc, aparcnii)     
            bg.remove_files([aparc])
        # make cerebellum
        refdir,_ = outdirs['refdir']
        cerebellum = os.path.join(refdir, 'grey_cerebellum.nii')
        if os.path.isfile(cerebellum):
            logging.warning('cerebellum %s exists, skipping'%(cerebellum))
            continue
        else:
            # copy aseg+aparc to refdir
            try:
                caparcnii = bg.copy_file(aparcnii, refdir)                        
                bg.make_cerebellum_nibabel(caparcnii)
                bg.remove_files([caparcnii])
            except:
                logging.warning('Fail: unable to make %s'%(cerebellum))
        
        rawtracer, exists = outdirs['rawtracer']
        tracerdir, _ = outdirs['tracerdir']
        if exists:
            logging.info('RAW %s data exists,'\
                         'remove %s to rerun'%(subid,rawtracer))
            continue
        else:        
            # Copy PET data, convert to nifti
            newraw = bg.copy_dir(petdir, rawtracer)
            
            ecats = bg.copy_dir(rawtracer, tracerdir, pattern='*.v')
            newname = '%s_%s' % (subid, tracer)
            bg.convertallecat(ecats, newname)
            logging.info('ecats converted for %s ' % (subid))                
            
