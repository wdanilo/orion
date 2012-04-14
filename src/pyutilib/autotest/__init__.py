#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________
#

__test__=False

import pyutilib.component.core
pyutilib.component.core.PluginGlobals.push_env('pyutilib.autotest')

from plugins import *
import yaml_plugin
import json_plugin
from driver import *
import default_testdriver

pyutilib.component.core.PluginGlobals.pop_env()
