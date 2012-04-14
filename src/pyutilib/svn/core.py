#!/usr/bin/env python
#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________
#
from logging import getLogger, StreamHandler, INFO
from formatter import NullWriter
from subprocess import Popen, PIPE

class SvnError(Exception):
    """Exception raised due to svn error."""

class PyutilibSvnFormatter(NullWriter):
    maxLvlLength = 7 # <- compute this?
    field = "%%-%is %%s" % (maxLvlLength+2)
    fill = "\n" + ' '*(maxLvlLength+2+1)

    def format(self, record):
        msg = record.getMessage().replace("\n", PyutilibSvnFormatter.fill)
        level = "(" + record.levelname + ")"
        return PyutilibSvnFormatter.field % ( level, msg )

log = getLogger('pyutilib.svn')
log_handler = StreamHandler()
log_handler.setFormatter(PyutilibSvnFormatter())
log.addHandler(log_handler)
log.setLevel(INFO)

SvnVersion = (0,0)
try:
    p = Popen( [ 'svn', '--version', '--quiet' ],  stdout=PIPE, stderr=PIPE )
    stdout, stderr = p.communicate()
    if p.returncode:
        raise SvnError( "svn --version returned error %i:\n%s" %
                        (p.returncode, stderr) )
    SvnVersion = ( int(stdout.split('.')[0]),  int(stdout.split('.')[1]) )
except SvnError:
    raise
except:
    raise SvnError("Error determining svn version: is subversion on your path?")

def VerifySvnVersion(minVersion):
    for i in range(len(minVersion)):
        if len(SvnVersion) <= i:
            return False
        elif minVersion[i] < SvnVersion[i]:
            return True
        elif minVersion[i] > SvnVersion[i]:
            return False
    return True
