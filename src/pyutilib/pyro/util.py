#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

__all__ = ['get_nameserver']

import os
import time
import Pyro.core
import Pyro.naming
from Pyro.errors import NamingError

def get_nameserver(host=None, num_retries=15):
    if not host is None:
        os.environ['PYRO_NS_HOSTNAME'] = host
    elif 'PYRO_NS_HOSTNAME' in os.environ:
        host = os.environ['PYRO_NS_HOSTNAME']
    Pyro.core.initServer()

    ns = None

    for i in xrange(0, num_retries):
        try:
            if host is None:
                ns=Pyro.naming.NameServerLocator().getNS()
            else:
                ns=Pyro.naming.NameServerLocator().getNS(host)
            break
        except NamingError, err:
            pass
        time.sleep(1)
        print "Failed to locate nameserver - trying again."        

    if ns is None:
        print "Could not locate nameserver after "+str(num_retries)+" attempts."
        raise SystemExit

    return ns
