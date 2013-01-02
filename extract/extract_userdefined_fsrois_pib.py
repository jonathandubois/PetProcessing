# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#!/usr/bin/env python

import sys, os, shutil
import wx
from glob import glob
sys.path.insert(0, '/home/jagust/cindeem/CODE/PetProcessing')
import preprocessing as pp
import base_gui as bg
import logging, logging.config
from time import asctime

if __name__ == '__main__':
    """Uses specified subject dir
    finds fdg dir
    find aparc_aseg in pet space
    finds pons normed pib
    """
    # start wx gui app
    app = wx.App()

    roifile = bg.FileDialog(prompt='Choose fsroi csv file',
                            indir ='/home/jagust/cindeem/CODE/PetProcessing')

    arda = '/home/jagust/arda/lblid'
    root = bg.SimpleDirDialog(prompt='Choose PIB data dir',
                              indir = '/home/jagust')
    userhome = os.environ['HOME']
    cleantime = asctime().replace(' ','-').replace(':', '-')
    logfile = os.path.join(userhome,
                           '%s_%s.log'%(__file__, cleantime))

    log_settings = pp.get_logging_configdict(logfile)
    logging.config.dictConfig(log_settings)
    
    tracer = 'PIB'
    user = os.environ['USER']
    logging.info('###START %s %s :::'%(tracer, __file__))
    logging.info('###TRACER  %s  :::'%(tracer))
    logging.info('###USER : %s'%(user))
    subs = bg.MyDirsDialog(prompt='Choose Subjects ',
                           indir='%s/'%root)
    roid = pp.roilabels_fromcsv(roifile)
    alld = {}
    for sub in subs:
        subid = None
        try:
            m = pp.re.search('B[0-9]{2}-[0-9]{3}_v[0-9]',sub)
            subid = m.group()
        except:
            logging.error('no visit marker in %s'%sub)
            subid = None
        if subid is None:
            try:
                m = pp.re.search('B[0-9]{2}-[0-9]{3}',sub)
                subid = m.group()
            except:
                logging.error('cant find ID in %s'%sub)
                continue        
            
        logging.info('%s'%subid)
        pth = os.path.join(sub, tracer.lower())
        if not os.path.isdir(pth):
            logging.error('%s does not exist, skipping'%pth)
            continue
                                
        # get dvr
        globstr = '%s/dvr/DVR*nii*'%(pth)
        dat = pp.find_single_file(globstr)
        if dat is None:
            logging.error('%s missing, skipping'%(globstr))
            continue
        dat = bg.unzip_file(dat)# in case zipped
        # get raparc
        globstr = '%s/coreg/rB*aparc_aseg.nii*'%(pth)
        raparc = pp.find_single_file(globstr)
        if raparc is None:
            logging.error('Missing %s, SKIPPING'%globstr)
            continue
        data = pp.nibabel.load(dat).get_data()
        meand = pp.mean_from_labels(roid, raparc, data)
        alld[subid] = meand

    ###write to file
    _, roifname = os.path.split(roifile)
    outf = os.path.join(userhome, 'roivalues_%s_%s_%s'%(tracer,
                                                        cleantime,
                                                        roifname))
    fid =open(outf, 'w+')
    fid.write('SUBID,')
    rois = sorted(meand.keys())
    roiss = ','.join(rois)
    fid.write(roiss)
    fid.write(',\n')
    for subid in sorted(alld.keys()):
        fid.write('%s,'%(subid))
        for r in rois:
            fid.write('%f,'%(alld[subid][r][0]))
        fid.write(',\n')
    fid.close()
    logging.info('Wrote %s'%(outf))
                      


        