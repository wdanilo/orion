#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

__all__ = ['Dispatcher', 'DispatcherServer']

import Pyro.core
import Pyro.naming
from Pyro.errors import NamingError
from Queue import Queue
from pyutilib.pyro.util import *

class Dispatcher(Pyro.core.ObjBase):

    def __init__(self, **kwds):
        Pyro.core.ObjBase.__init__(self)
        self.default_taskqueue = Queue()
        self.default_resultqueue = Queue()
        self.taskqueue = {}
        self.resultqueue = {}
        self.verbose = kwds.get("verbose", False)
        if self.verbose is True:
           print "Verbose output enabled..."

    def shutdown(self):
        print "Dispatcher received request to shut down - initiating..."
        self.getDaemon().shutdown()

    def add_task(self, task, type=None):
        if self.verbose is True:
           print "Received request to add task="+str(task)+"; queue type="+str(type)
        if type is None:
            self.default_taskqueue.put(task)
        else:
            if not type in self.taskqueue:
                self.taskqueue[type] = Queue()
            self.taskqueue[type].put(task)

    def get_task(self, type=None, timeout=5):
        if self.verbose is True:
           print "Received request for a task from queue type="+str(type)+"; timeout="+str(timeout)+" seconds"
        if type is None:
            return self.default_taskqueue.get(block=True, timeout=timeout)
        else:
            try:
                return self.taskqueue[type].get(block=True, timeout=timeout)
            except KeyError:
                return None

    def add_result(self, data, type=None):
        if self.verbose is True:
           print "Received request to add result with data="+str(data)+"; queue type="+str(type)
        if type is None:
            self.default_resultqueue.put(data)
        else:
            if not type in self.resultqueue:
                self.resultqueue[type] = Queue()
            self.resultqueue[type].put(data)

    def get_result(self, type=None, timeout=5):
        if self.verbose is True:
           print "Received request for result with queue type="+str(type)+"; timeout="+str(timeout)
        if type is None:
            return self.default_resultqueue.get(block=True, timeout=timeout)
        else:
            try:
                return self.resultqueue[type].get(block=True, timeout=timeout)
            except KeyError:
                return None

    def num_tasks(self, type=None):
        if self.verbose is True:
           print "Received request for number of tasks in queue with type="+str(type)
        if type is None:
            return self.default_taskqueue.qsize()
        else:
            try:
                self.taskqueue[type].get(block=True, timeout=timeout)
            except KeyError:
                return 0

    def num_results(self, type=None):
        if self.verbose is True:
           print "Received request for number of results in queue with type="+str(type)
        if type is None:
            return self.default_resultqueue.qsize()
        else:
            try:
                self.resultqueue[type].get(block=True, timeout=timeout)
            except KeyError:
                return 0

    def queues_with_results(self):
        if self.verbose is True:
           print "Received request for the set of queues with results"
        result = set()
        if self.default_resultqueue.qsize() > 0:
            result.add(None)
        for queue_name, result_queue in self.resultqueue.items():
           if result_queue.qsize() > 0:
               result.add(queue_name)
        return result        

def DispatcherServer(group=":PyUtilibServer", host=None, verbose=False):
    #
    # main program
    #
    ns = get_nameserver(host)
    if ns is None:
        return

    daemon=Pyro.core.Daemon()
    daemon.useNameServer(ns)

    try:
        ns.createGroup(group)
    except NamingError:
        pass
    try:
        ns.unregister(group+".dispatcher")
    except NamingError:
        pass

    # the default value of 200 on clusters wasn't working well for large jobs.
    Pyro.config.PYRO_MAXCONNECTIONS = 1000 

    uri=daemon.connect(Dispatcher(verbose=verbose),group+".dispatcher")

    print "Dispatcher is ready."
    daemon.requestLoop()
