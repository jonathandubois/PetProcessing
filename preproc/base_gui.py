# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
import wx
import sys, os
import tempfile
import wx.lib.agw.multidirdialog as mdd
from glob import glob
import nibabel as ni
import nipype
from nipype.interfaces.base import CommandLine
from nipype.interfaces.fsl import Split as fsl_split
import nipype.interfaces.dcm2nii as dcm2nii
import numpy as np
import logging

from PySide import QtCore, QtGui

   
def qt_dirs(indir = '/home/jagust', caption='Select Subjects'):
    app = QtGui.QApplication(sys.argv)
    win = QtGui.QMainWindow()
    file_dialog = QtGui.QFileDialog(win, caption=caption)
    file_dialog.setFileMode(QtGui.QFileDialog.DirectoryOnly)
    file_dialog.setDirectory(indir)
    tree_view = file_dialog.findChild(QtGui.QTreeView)
    tree_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
    list_view = file_dialog.findChild(QtGui.QListView, "listView")
    list_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

    if file_dialog.exec_() == QtGui.QDialog.Accepted:
            files =  file_dialog.selectedFiles()
    else:
            files = file_dialog.getOpenFileNames(win, "", "/")
    win.destroy()
    app.quit()
    return files
    
def TextEntry(message='Enter Directory Glob', default = 'rpons_tunormed_mean*'):
    """Text entry dialog to help specify directory or file to search for"""
    dlg = wx.TextEntryDialog(None,
                             message = message,
                             defaultValue = default)
    if dlg.ShowModal() == wx.ID_OK:
        outstr = dlg.GetValue()
    else:
        outstr = ''
    dlg.Destroy()
    return outstr

def MyDirsDialog(prompt='Choose Subject Dirs',
        indir='',title='Choose Subject Dirs'):
    """
    Advanced  directory dialog and returns selected directories
    """

    #agwStyle=MDD.DD_MULTIPLE|MDD.DD_DIR_MUST_EXIST
    dlg = mdd.MultiDirDialog(None,
                             message=prompt,
                             title=title,
                             defaultPath=indir,
                             style = mdd.DD_MULTIPLE)
    if dlg.ShowModal() == wx.ID_OK:
      tmpdir = dlg.GetPaths()
    else:
      tmpdir = []
    dlg.Destroy()
    ## fix weird HOME DIR bug
    env = os.environ
    home = env['HOME']
    tmpdir = [x.replace('Home directory', home) for x in tmpdir]
    return tmpdir


                       
def FileDialog(prompt='ChooseFile', indir=''):
    """
    opens a wx dialog that allows you to select a single
    file, and returns the full path/name of that file """
    dlg = wx.FileDialog(None,
                        message = prompt,
                        defaultDir = indir)
                        
    if dlg.ShowModal() == wx.ID_OK:
          outfile = dlg.GetPath()
    else:
          outfile = None
    dlg.Destroy()
    return outfile

def FilesDialog(prompt = 'Choose Files', indir = ''):
      """
      opens a wx Dialog that allows you to select multiple files within
      a single directory and returns full path/names of those files"""
      fdlg = wx.FileDialog(None,
                           message=prompt,
                           defaultDir = indir,
                           style = wx.FD_MULTIPLE)
      if fdlg.ShowModal() == wx.ID_OK:
            outfiles = fdlg.GetPaths()
      else:
            outfiles = None
      fdlg.Destroy()
      return outfiles

def SimpleDirDialog(prompt='Choose Directory', indir=''):
    """
    opens a directory dialog and returns selected directory
    """
    sdlg = wx.DirDialog(None,
                        message = prompt,
                        defaultPath = indir)
    if sdlg.ShowModal() == wx.ID_OK:
          tmpdir = sdlg.GetPath()
    else:
          tmpdir = []
    sdlg.Destroy()
    return tmpdir
    
def MyVisitDialog():
    choices = ['v1', 'v2', 'v3', 'v4', 'v5']
    dialog = wx.SingleChoiceDialog(None,
                                   'Choose a Timepoint',
                                   'VISIT TIMEPOINT',
                                   choices)
    if dialog.ShowModal() == wx.ID_OK:
        visit = dialog.GetStringSelection()
    dialog.Destroy()
    return visit
    
def MyTracerDialog():
    choices = ['FDG',  'PIB', 'AV45']
    dialog = wx.SingleChoiceDialog(None,
                                   'Choose a Tracer',
                                   'TRACERS',
                                   choices)
    if dialog.ShowModal() == wx.ID_OK:
        tracer = dialog.GetStringSelection()
    dialog.Destroy()
    return tracer

def MyScanChoices(choices,message = 'Choose directories'):
    sdialog = wx.MultiChoiceDialog(None,
                                  message = message,
                                  caption='Choices',
                                  choices=choices)
    if sdialog.ShowModal() == wx.ID_OK:
        dirs = sdialog.GetSelections()
    sdialog.Destroy()
    return [choices[x] for x in dirs]


def MyRadioSelect(outdict):
      mrc = MyRadioChoices(outdict)
      mrc_retval = mrc.ShowModal()
      if mrc_retval == wx.ID_OK:
            outdict = mrc.GetValue()
      mrc.Destroy()
      return outdict

def MriDialog(subid):
      qdlg = wx.MessageDialog(None,
                              message = 'No Freesurfer MRI for ' + \
                              '%s, skip subject?'%(subid),
                              caption = 'MRI Message',
                              style=wx.YES_NO)
     
      if qdlg.ShowModal() == wx.ID_YES:
            resp = True

      else:
            resp = False
      
      qdlg.Destroy()
      return resp

class MyRadioChoices(wx.Dialog):
      
      def __init__(self, outdict):
            #global outdict
            self.outdict = outdict
            nchoices = len(outdict)
            wx.Dialog.__init__(self, None, -1, 'Radio select', size=(800,800),
                               )
            panel = wx.Panel(self,-1)
            self.button = wx.Button(panel, wx.ID_OK, 'Finished',
                                    pos = (10,10))
            self.Bind(wx.EVT_CLOSE, self.DialogClose)
            #self.scroll = wx.ScrolledWindow(panel, -1)
            #self.scroll.SetScrollbars( 100, 100, 600, nchoices*100) 
            dirlist = ['Controls', 'AD', 'LPA', 'PCA', 'FTLD', 'CBS',
                       'Others', 'NIFD-LBL', 'NIFD-ADNI', 'MCI']
            self.rb = {}
            for val, item in enumerate(sorted(outdict.keys())):
                  self.rb.update({item:wx.RadioBox(panel, -1, item, (10, 50+val*40),
                                                   (550,40), dirlist,
                                                   1, wx.RA_SPECIFY_ROWS)})

      def DialogClose(self, event):
            self.EndModal(wx.ID_OK)
      def GetValue(self):
            for key in self.rb:
                  self.outdict[key][1] = self.rb[key].GetStringSelection()
            #print self.outdict
            return self.outdict
                  
def singlechoice(options, text='Start Time'):
    dlg = wx.SingleChoiceDialog(None,text, text, options, wx.CHOICEDLG_STYLE)
    if dlg.ShowModal() == wx.ID_OK:
        choice = dlg.GetStringSelection()
    else:
        choice = None
    dlg.Destroy()
    return choice

            
            
#### END WX ###

      
if __name__ == '__main__':

    print 'Im a module named %s'%__file__
    
