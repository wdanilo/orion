#
# Unit Tests for util/singleton
#
#

import os
import sys
from os.path import abspath, dirname
sys.path.insert(0, dirname(dirname(abspath(__file__)))+os.sep+".."+os.sep+"..")
currdir = dirname(abspath(__file__))+os.sep

import unittest
from nose.tools import nottest
import pyutilib.misc


class A(pyutilib.misc.MonoState):

    def __init__(self):
        self.state = True

class B(pyutilib.misc.Singleton):

    def __init__(self):
        self.state = True


class SingletonDebug(unittest.TestCase):

    def test_A(self):
        """Verify that MonoState generates one global state"""
        a1 = A()
        a2 = A()
        self.assertNotEqual(a1,a2)
        self.assertEqual(a1.__dict__,a2.__dict__)

    def test_B(self):
        """Verify that Singleton generates one instance"""
        b1 = B()
        b2 = B()
        self.assertEqual(b1,b2)


if __name__ == "__main__":
    unittest.main()
