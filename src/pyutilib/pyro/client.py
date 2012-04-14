#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

__all__ = ['Client']

import Pyro.core
import Queue
import os, socket
from pyutilib.pyro.util import *
from Pyro.errors import NamingError
import time

class Client(object):

    def __init__(self, group=":PyUtilibServer", type=None, host=None, num_dispatcher_tries=15):
        self.type=type
        self.id = 0
        Pyro.core.initClient()
        self.ns = get_nameserver(host)
        if self.ns is None:
            raise RuntimeError, "Client failed to locate Pyro name server on the network!"
        print 'Attempting to find Pyro dispatcher object...'
        self.URI = None
        for i in xrange(0,num_dispatcher_tries): 
            try:
                self.URI=self.ns.resolve(group+".dispatcher")
                print 'Dispatcher Object URI:',self.URI
                break
            except NamingError, x:
                pass
            time.sleep(1)
            print "Failed to find dispatcher object from name server - trying again."
        if self.URI is None:
            print 'Could not find dispatcher object, nameserver says:',x
            raise SystemExit
        self.set_group(group)
        self.CLIENTNAME = "%d@%s" % (os.getpid(), socket.gethostname())
        print "This is client",self.CLIENTNAME

    def set_group(self, group):
        self.dispatcher = Pyro.core.getProxyForURI(self.URI)

    def add_task(self, task, override_type=None, verbose=False):
        if task.id is None:
            task.id = self.CLIENTNAME + "_" + str(self.id)
            self.id += 1
        else:
            task.id = self.CLIENTNAME + "_" + str(task.id)
        if verbose is True:
            if self.type is not None:
                print "Adding task",task.id,"to dispatcher queue with type=",self.type
            else:
                print "Adding task",task.id,"to dispatcher queue"
        if override_type is not None:
           self.dispatcher.add_task(task, type=override_type)
        else:
           self.dispatcher.add_task(task, type=self.type)

    def get_result(self, override_type=None):
        try:
            if override_type is not None:
               return self.dispatcher.get_result(type=override_type)
            else:
               return self.dispatcher.get_result(type=self.type)
        except Queue.Empty:
            return None

    def num_tasks(self, override_type=None):
        if override_type is not None:
           return self.dispatcher.num_tasks(type=override_type)
        else:
           return self.dispatcher.num_tasks(type=self.type)

    def num_results(self, override_type=None):
        if override_type is not None:
           return self.dispatcher.num_results(type=override_type)
        else:
           return self.dispatcher.num_results(type=self.type)

    def queues_with_results(self):
        return self.dispatcher.queues_with_results()
