#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

class Task(object):

    def __init__(self, id=None, data=None):
        self.id=id
        self.data=data
        self.result=None
        self.processedBy=None
        self.type=None

    def __str__(self):
        return "<Task id=%s>" % str(self.id)
