#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

"""A plugin that manages temporary files."""

__all__ = ['ITempfileManager', 'TempfileManagerPlugin', 'TempfileManager']

from options import *
from managed_plugin import *
import sys
import os
import tempfile


class ITempfileManager(Interface):
    """Interface for managing temporary files."""

    def create_tempfile(self, suffix=None, prefix=None, text=False, dir=None):
        """Return the absolute path of a temporary filename that is guaranteed to be unique."""

    def add_tempfile(self, filename):
        """Declare this file to be temporary."""

    def clear_tempfiles(self):
        """Delete all temporary files."""

    def sequential_files(self, ctr=0):
        """Start generating sequential files, using the specified counter"""

    def unique_files(self):
        """Start generating unique files"""


class TempfileManagerPlugin(ManagedSingletonPlugin):
    """A plugin that manages temporary files."""

    implements(ITempfileManager)

    def __init__(self, **kwds):
        kwds['name']='TempfileManager'
        ManagedSingletonPlugin.__init__(self,**kwds)
        self._tempfiles = []
        declare_option("tempdir", default=None)
        self._ctr=-1

    def create_tempfile(self, suffix=None, prefix=None, text=False, dir=None):
        """
        Return the absolute path of a temporary filename that is
        guaranteed to be unique.  This function generates the file and returns
        the filename.
        """
        if suffix is None:
            suffix=''
        if prefix is None:
            prefix='tmp'
        if dir is None:
            dir=self.tempdir
        if self._ctr >= 0:
            fname = dir+os.sep+prefix+str(self._ctr)+suffix
            self._ctr += 1
        else:
            ans = tempfile.mkstemp(suffix=suffix, prefix=prefix, text=text, dir=dir)
            ans = list(ans)
            if not os.path.isabs(ans[1]):
                fname = dir+os.sep+ans[1]
            else:
                fname = ans[1]
            os.close(ans[0])
        self._tempfiles.append(fname)
        if os.path.exists(fname):
            os.remove(fname)
        return fname

    def add_tempfile(self, filename):
        """Declare this file to be temporary."""
        tmp = os.path.abspath(filename)
        if not os.path.exists(tmp):
            raise IOError, "Temporary file does not exist: "+tmp
        self._tempfiles.append(tmp)

    def clear_tempfiles(self):
        """Delete all temporary files."""
        for file in self._tempfiles:
            if os.path.exists(file):
                os.remove(file)
        self._tempfiles=[]

    def sequential_files(self, ctr=0):
        """Start generating sequential files, using the specified counter"""
        self._ctr=ctr

    def unique_files(self):
        """Start generating sequential files, using the specified counter"""
        self._ctr=-1

#
# This global class provides a convenient handle to this
# singleton plugin
#
TempfileManager = TempfileManagerPlugin()
