#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

import sys

_old_stdout = []
_old_stderr = []
_local_file = True

def setup_redirect(output):
    """
    Redirect stdout and stderr to a specified output, which
    is either the string name for a file, or a file-like class.
    """
    global _old_stdout
    global _old_stderr
    global _local_file
    _old_stdout.append(sys.stdout)
    _old_stderr.append(sys.stderr)
    if isinstance(output, basestring):
        sys.stderr = _Redirecter(output)
        _local_file=True
    else:
        sys.stderr = output
        _local_file=False
    sys.stdout = sys.stderr

def reset_redirect():
    """ Reset redirection to use standard stdout and stderr """
    global _old_stdout
    global _old_stderr
    if not _old_stdout is []:
        if _local_file:
            sys.stdout.close()
        sys.stdout = _old_stdout.pop()
        sys.stderr = _old_stderr.pop()

#
# A class used to manage the redirection of IO.  The sys.stdout and
# sys.stderr values are set to an instance of this class.
#
class _Redirecter:

    def __init__(self, ofile):
        """ Constructor. """
        self.ofile = ofile
        self._out = open(ofile,"w")

    def write(self, s):
        """ Write an item. """
        self._out.write(s)

    def flush(self):
        """ Flush the output. """
        self._out.flush()

    def close(self):
        """ Close the stream. """
        self._out.close()
