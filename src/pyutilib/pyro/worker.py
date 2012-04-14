#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

__all__ = ['TaskWorker', 'TaskWorkerServer']

import Pyro.core
import Queue
import os, socket, time
import pyutilib.pyro
from pyutilib.pyro.util import *
from Pyro.errors import NamingError,ConnectionClosedError,ConnectionDeniedError

class TaskWorker(object):

    def __init__(self, group=":PyUtilibServer", type=None, host=None, num_dispatcher_tries=15):
        self.type=type
        Pyro.core.initClient()
        self.ns = get_nameserver(host)
        if self.ns is None:
            raise RuntimeError, "TaskWorker failed to locate Pyro name server on the network!"            
        print 'Attempting to find Pyro dispatcher object...'
        URI = None
        for i in xrange(0,num_dispatcher_tries):         
            try:
                URI=self.ns.resolve(group+".dispatcher")
                print 'Dispatcher Object URI:',URI
                break
            except NamingError, x:
                pass
            time.sleep(1)
            print "Failed to find dispatcher object from name server - trying again."
        if URI is None:
            print 'Could not find dispatcher object, nameserver says:',x
            raise SystemExit
        self.dispatcher = Pyro.core.getProxyForURI(URI)
        self.WORKERNAME = "Worker_%d@%s" % (os.getpid(), socket.gethostname())
        print "This is worker",self.WORKERNAME

    def run(self):

        print "Listening for work from dispatcher..."

        while 1:
            try:
                task = self.dispatcher.get_task(type=self.type)
            except Queue.Empty:
                pass
            except ConnectionDeniedError, str:
                # this can happen if the dispatcher is overloaded. 
                pass     
                print "***WARNING: Connection to dispatcher server denied - message="+str
                print "            A potential remedy may be to increase PYRO_MAXCONNECTIONS from its current value of "+str(Pyro.config.PYRO_MAXCONNECTIONS)
                time.sleep(0.1) # sleep for a bit longer than normal, for obvious reasons
            else:

                if task is None:
                   # if the queue hasn't been defined yet, None is returned immediately
                   # by the dispatcher. this isn't ideal, as it leads to a lot of burned
                   # cycles waiting until the first work task is submitted to the dispatch
                   # server. 
                   # TBD: MAYBE WE SHOULD SLEEP FOR A SHORT PERIOD, TO EMULATE A TIMEOUT?
                   pass
                else:
                   #
                   # NOTE: should we return a task with an
                   # empty data element?  It isn't clear that we
                   # need to send _back_ the data, but the factor
                   # example takes advantage of the fact that it's sent
                   # back...
                   #
                   task.result = self.process(task.data)
                   task.processedBy = self.WORKERNAME
                   self.dispatcher.add_result(task, type=self.type)

                   # give the dispatch server a bit of time to recover and process the request -
                   # it is very unlikely that it can have another task ready (at least in most
                   # job distribution structure) right away.

                   # TBD: We really need to parameterize the time-out value.
                   time.sleep(0.01)

def TaskWorkerServer(cls, **kwds):
    host=None
    if 'argv' in kwds:
        argv = kwds['argv']
        if len(argv) == 2:
            host=argv[1]
        kwds['host'] = host
        del kwds['argv']
    worker = cls(**kwds)
    if worker.ns is None:
        return
    try:
        worker.run()
    except ConnectionClosedError:
        print "Lost connection to dispatch server - shutting down..."
