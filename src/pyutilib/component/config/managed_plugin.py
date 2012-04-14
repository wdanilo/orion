#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

"""Plugins that contain options that support configuration of their services."""

__all__ = ['ManagedPlugin', 'ManagedSingletonPlugin']

from options import *


class ManagedPlugin(Plugin):
    """A plugin that has an option supports configuration of this service."""

    def __init__(self, **kwds):
        Plugin.__init__(self,**kwds)
        #super(ManagedPlugin,self).__init__(**kwds)
        declare_option(name=self.name, section="Services", local_name="enable", default=self._enable, cls=BoolOption, doc="Option that controls behavior of service %s." % self.name)


class ManagedSingletonPlugin(SingletonPlugin):
    """A singleton plugin that has an option supports configuration of this service."""

    def __init__(self, **kwds):
        Plugin.__init__(self,**kwds)
        #super(ManagedSingletonPlugin,self).__init__(**kwds)
        declare_option(name=self.name, section="Services", local_name="enable", default=self._enable, cls=BoolOption, doc="Option that controls behavior of service %s." % self.name )
