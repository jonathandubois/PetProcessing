# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import unittest
import sys, os
import tempfile
from datetime import datetime
import csv
from glob import glob

import nibabel.ecat as ecat
import dicom
import numpy as np
from numpy.testing import assert_equal
import pandas

from .. import frametimes as ft

class TestFrametimes(unittest.TestCase):
    def setUp(self):
        pth, nme = os.path.split(__file__)
        ecats = sorted(glob(os.path.join(pth, '*.v')))
        self.ecats = ecats
        bio_csv = os.path.join(pth, 'PIBtiming_B00-000.csv')
        self.bio = bio_csv

    def test_frametime_from_ecat(self):
        infile = self.ecats[0]
        times = ft.frametime_from_ecat(infile)
        assert_equal(times[0,0], 1.0)
        assert_equal(times[0,1], 0.0)#start time
        assert_equal(times[1,2], 600000.0) #endtime second frame
        assert_equal(times[1,3], 300000.0) # frame 2 duration

    def test_frametimes_from_ecat(self):
        allv  = self.ecats
        ft_all = ft.frametimes_from_ecats(allv)
        assert_equal(ft_all[-1,0],6.0)
        assert_equal(ft_all[-1,1] > ft_all[-2,1], True)

    def test_make_outfile(self):
        infile = tempfile.NamedTemporaryFile() 
        # test naming
        outf = ft.make_outfile(infile.name)
        np.testing.assert_equal('frametimes' in outf, True)
        infile.close()
    
    def test_write_frametimes(self):
        # test writing
        ft_all = ft.frametimes_from_ecats(self.ecats) 
        ft_sec = ft_all[0,:].copy()
        ft_sec.shape = (1,4)
        ft_sec[:,1:] = ft_sec[:,1:] / 1000.
        tmpfile = tempfile.NamedTemporaryFile()
        outf = ft.make_outfile(tmpfile.name)
        ft.write_frametimes(ft_sec, outf)
        outf_sec = ft.make_outfile(tmpfile.name, name = 'frametimes_sec')
        ft.write_frametimes(ft_sec, outf_sec)

        # roundtrip
        newft = ft.read_frametimes(outf)
        assert_equal(newft[0,0], ft_sec[0,0])
        assert_equal(newft[0,1], ft_sec[0,1])
        assert_equal(newft[0,2], ft_sec[0,2])
        assert_equal(newft[0,3], ft_sec[0,3])
        ## clean up
        os.unlink(outf_sec)
        os.unlink(outf)
        tmpfile.close() #
    
