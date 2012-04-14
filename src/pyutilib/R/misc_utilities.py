#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

import os
import re
import sys
import string



#
# A class that can be used to store a bunch of data dynamically
#
# foo = Bunch(data=y, sq=y*y, val=2)
# print foo.data
# print foo.sq
# print foo.val
#
# Adapted from code developed by Alex Martelli and submitted to
# the ActiveState Programmer Network http://aspn.activestate.com
#
class Bunch(dict):
    def __init__(self, **kw):
        dict.__init__(self,kw)
        self.__dict__.update(kw)
