#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________

"""A parser used by the Configuration class."""

__all__ = ['Configuration_ConfigParser']

from configuration import *
import os.path
import ConfigParser
from managed_plugin import *
try:
    from ordereddict import OrderedDict
except:
    OrderedDict = dict

#
# Force the config file option manager to be case sensitive
#
ConfigParser.RawConfigParser.optionxform = str


class Configuration_ConfigParser(ManagedSingletonPlugin):
    """A configuration parser that uses the ConfigParser package."""

    implements(IConfiguration)

    def __init__(self, **kwds):
        kwds['name']='Configuration_ConfigParser'
        ManagedSingletonPlugin.__init__(self,**kwds)

    def load(self, filename):
        """Returns a list of tuples: [ (section,option,value) ]"""
        parser = ConfigParser.ConfigParser()
        if not os.path.exists(filename):
            raise ConfigurationError, "File "+filename+" does not exist!"
        parser.read(filename)
        #
        # Collect data
        #
        data = []
        for section in parser.sections():
            for (option,value) in parser.items(section):
                data.append( (section,option,value) )
        return data

    def save(self, filename, config, header=None):
        """Save configuration information to the specified file."""
        if sys.version_info[:2] == (2,6):
            parser = ConfigParser.ConfigParser(dict_type=OrderedDict)
        else:
            parser = ConfigParser.ConfigParser()
        for (section,option,value) in config:
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section,option,value)
        OUTPUT=open(filename,"w")
        if not header is None:
            for line in header.split("\n"):
                print >>OUTPUT, "; "+line
        parser.write(OUTPUT)
        OUTPUT.close()
